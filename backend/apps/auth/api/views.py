from http import HTTPStatus
from typing import override

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from dmr import APIError, Body, ResponseSpec, modify, validate
from dmr.endpoint import ValidateAnyCallable
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.jwt import request_jwt
from dmr.security.jwt.blocklist import JWTokenBlocklistSyncMixin
from dmr.security.jwt.views import (
    CookieLogoutSyncController,
    CookieObtainTokensSyncController,
    CookieRefreshTokensSyncController,
    ObtainTokensPayload,
)

from apps.users.api.schemas import MeOut
from apps.users.api.views import serialize_me
from apps.users.models import User

from .controllers import AuthenticatedController
from .schemas import LoginPayload, PasswordChangeIn
from .security import access_token_auth


# The refresh cookie is scoped to this path only, so it is never sent
# with any other request - including `/auth/logout/`. That is a
# deliberate trade-off: `LogoutController.revoke_tokens()` below can
# only blocklist the access token used to authenticate the logout
# call, not the refresh token. A refresh token that leaked before
# logout stays valid until it expires naturally. Widening this path
# would let logout revoke both, at the cost of sending the refresh
# cookie to more than just the refresh endpoint.
REFRESH_COOKIE_PATH = "/api/v1/auth/refresh/"


class _CookieSecurity:
    """Send the auth cookies as `secure` outside local development.

    Shared by every controller that issues or discards these cookies, so
    the `secure` flag can't drift between them - the browser only lets a
    ``Set-Cookie`` clear an existing cookie when `path`/`domain`/`secure`
    all match how it was originally set.
    """

    jwt_cookie_secure = not settings.DEBUG


def _serialized_request_user(controller) -> MeOut:
    return serialize_me(controller.request, controller.request.user)


class LoginController(
    _CookieSecurity,
    CookieObtainTokensSyncController[
        PydanticFastSerializer,
        LoginPayload,
        MeOut,
    ],
):
    """`POST /api/v1/auth/login/` - exchange email+password for cookies."""

    jwt_refresh_cookie_path = REFRESH_COOKIE_PATH
    response_status_code = HTTPStatus.OK

    @override
    def convert_auth_payload(self, payload: LoginPayload) -> ObtainTokensPayload:
        # `authenticate()` is called with these kwargs. Even though our
        # USERNAME_FIELD is "email", Django's ModelBackend still expects
        # the value under the "username" kwarg name.
        return {"username": payload.email, "password": payload.password}

    @override
    def make_api_response(self) -> MeOut:
        return _serialized_request_user(self)

    @classmethod
    def _post_spec(cls) -> ValidateAnyCallable:
        # `.lazy()` runs after our overrides (e.g. `jwt_refresh_cookie_path`)
        # are already in place, so `cls.issued_cookies_spec()` etc. below
        # reflect this subclass, not the framework's own defaults.
        return validate(
            ResponseSpec(
                MeOut,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies={**cls.issued_cookies_spec(), **cls.csrf_cookie_spec()},
                description="The now-authenticated user.",
            ),
            ResponseSpec(
                return_type=cls.error_model,
                status_code=HTTPStatus.UNAUTHORIZED,
            ),
            summary="Log in",
            description=(
                "Authenticate with an email and password. On success, "
                "the access and refresh tokens are set as `httponly` "
                "cookies - they are never exposed to the response body "
                "or to JavaScript - and the authenticated user is "
                "returned.\n\n"
                "- The **access token** cookie is sent with every API "
                "request and is short-lived.\n"
                "- The **refresh token** cookie is only sent to "
                f"`POST {REFRESH_COOKIE_PATH}` and is long-lived."
            ),
            tags=["Auth"],
        )

    @validate.lazy(_post_spec)
    @override
    def post(self, parsed_body: Body[LoginPayload]) -> HttpResponse:
        return super().post(parsed_body)


class RefreshController(
    # Since DMR 0.15.0, this mixin also works when mixed into a refresh
    # controller (previously it only worked on auth classes), so the
    # blocklist check for revoked refresh tokens no longer needs a manual
    # override: `check_auth()` now covers it.
    _CookieSecurity,
    JWTokenBlocklistSyncMixin,
    CookieRefreshTokensSyncController[
        PydanticFastSerializer,
        MeOut,
    ],
):
    """`POST /api/v1/auth/refresh/` - rotate cookies using the refresh cookie."""

    jwt_refresh_cookie_path = REFRESH_COOKIE_PATH
    response_status_code = HTTPStatus.OK

    @override
    def make_api_response(self) -> MeOut:
        return _serialized_request_user(self)

    @classmethod
    def _post_spec(cls) -> ValidateAnyCallable:
        return validate(
            ResponseSpec(
                MeOut,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies=cls.issued_cookies_spec(),
                description="The authenticated user.",
            ),
            ResponseSpec(
                return_type=cls.error_model,
                status_code=HTTPStatus.UNAUTHORIZED,
            ),
            *cls.csrf_response_specs(),
            summary="Refresh tokens",
            description=(
                "Exchange a valid, non-revoked refresh cookie for a "
                "brand new pair of cookies, without sending the user's "
                "password again. There is no request body: the browser "
                "sends the refresh cookie on its own."
            ),
            tags=["Auth"],
        )

    @validate.lazy(_post_spec)
    @override
    def post(self) -> HttpResponse:
        return super().post()


class LogoutController(
    _CookieSecurity,
    CookieLogoutSyncController[PydanticFastSerializer],
):
    """`POST /api/v1/auth/logout/` - drop cookies and revoke the access token."""

    request: AuthenticatedHttpRequest[User]
    auth = (access_token_auth,)
    # Signing out has to work for someone who still owes a new password.
    allows_pending_password_change = True
    # Needed so the discard `Set-Cookie` for the refresh cookie is scoped
    # to the same path it was originally issued with - otherwise the
    # browser won't recognize it as the same cookie and won't clear it.
    jwt_refresh_cookie_path = REFRESH_COOKIE_PATH

    @override
    def revoke_tokens(self) -> None:
        # Only the access token used to authenticate this request can be
        # revoked here - the refresh cookie is scoped to
        # `REFRESH_COOKIE_PATH` and is therefore never sent with this
        # request. See the `REFRESH_COOKIE_PATH` comment above.
        access_token_auth.blocklist(request_jwt(self.request, strict=True))

    @classmethod
    def _post_spec(cls) -> ValidateAnyCallable:
        return validate(
            ResponseSpec(
                None,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies=cls.discarded_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
            summary="Log out",
            description=(
                "Revoke the access token used to authenticate this "
                "request, so it can no longer be used even if it has "
                "not expired yet, and drop both token cookies. The "
                "refresh token is not revoked server-side - it is only "
                "dropped client-side - and stays valid until it "
                "expires naturally."
            ),
            tags=["Auth"],
        )

    @validate.lazy(_post_spec)
    @override
    def post(self) -> HttpResponse:
        return super().post()


class PasswordController(AuthenticatedController[PydanticSerializer]):
    """`POST /api/v1/auth/password/` - change your own password."""

    # This is the one thing an account with a temporary password may do.
    allows_pending_password_change = True

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Change password",
        description=(
            "Change the signed-in user's password. The current password "
            "has to be sent too, and the new one has to pass the server's "
            "password rules. This also ends the obligation to choose a new "
            "password of an account created with a temporary one."
        ),
        extra_responses=[ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST)],
        tags=["Auth"],
    )
    def post(self, parsed_body: Body[PasswordChangeIn]) -> None:
        user = self.request.user
        if not user.check_password(parsed_body.current_password):
            raise self._bad_request(
                "The current password is wrong.", "current_password"
            )
        try:
            validate_password(parsed_body.new_password, user)
        except DjangoValidationError as exc:
            raise self._bad_request(" ".join(exc.messages), "new_password") from exc

        user.set_password(parsed_body.new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])

    def _bad_request(self, message: str, field: str) -> APIError:
        return APIError(
            self.format_error(message, loc=[field], error_type=ErrorType.value_error),
            status_code=HTTPStatus.BAD_REQUEST,
        )

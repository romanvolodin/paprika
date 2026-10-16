from http import HTTPStatus
from typing import override

from django.conf import settings
from django.http import HttpResponse
from dmr import Body, ResponseSpec, validate
from dmr.endpoint import ValidateAnyCallable
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.jwt import request_jwt
from dmr.security.jwt.auth import CookieJWTSyncAuth
from dmr.security.jwt.blocklist import JWTokenBlocklistSyncMixin
from dmr.security.jwt.views import (
    CookieLogoutSyncController,
    CookieObtainTokensSyncController,
    CookieRefreshTokensSyncController,
    ObtainTokensPayload,
)

from apps.users.api.schemas import UserOut
from apps.users.models import User

from .schemas import LoginPayload


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


class AccessTokenAuth(CookieJWTSyncAuth):
    """Cookie JWT auth that only accepts access tokens.

    ``CookieJWTSyncAuth`` on its own does not check the ``type`` claim we
    put into the token's ``extras``, so a refresh token would otherwise
    work just as well as an access token on any protected endpoint.
    """

    @override
    def check_auth(self, user, token) -> None:
        super().check_auth(user, token)
        if token.extras.get("type") != "access":
            from dmr.exceptions import NotAuthenticatedError  # noqa: PLC0415

            raise NotAuthenticatedError("Invalid token type.")


class AccessTokenBlocklistAuth(JWTokenBlocklistSyncMixin, AccessTokenAuth):
    """Access token auth that also honors the revoked-tokens blocklist."""


access_token_auth = AccessTokenBlocklistAuth()


def _serialized_request_user(controller) -> UserOut:
    # Imported lazily: `apps.users.api.views` imports `access_token_auth`
    # from this module at module load time, so a top-level import here
    # would be circular.
    from apps.users.api.views import _serialize_user  # noqa: PLC0415

    return _serialize_user(controller.request, controller.request.user)


class LoginController(
    _CookieSecurity,
    CookieObtainTokensSyncController[
        PydanticFastSerializer,
        LoginPayload,
        UserOut,
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
    def make_api_response(self) -> UserOut:
        return _serialized_request_user(self)

    @classmethod
    def _post_spec(cls) -> ValidateAnyCallable:
        # `.lazy()` runs after our overrides (e.g. `jwt_refresh_cookie_path`)
        # are already in place, so `cls.issued_cookies_spec()` etc. below
        # reflect this subclass, not the framework's own defaults.
        return validate(
            ResponseSpec(
                UserOut,
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
        UserOut,
    ],
):
    """`POST /api/v1/auth/refresh/` - rotate cookies using the refresh cookie."""

    jwt_refresh_cookie_path = REFRESH_COOKIE_PATH
    response_status_code = HTTPStatus.OK

    @override
    def make_api_response(self) -> UserOut:
        return _serialized_request_user(self)

    @classmethod
    def _post_spec(cls) -> ValidateAnyCallable:
        return validate(
            ResponseSpec(
                UserOut,
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

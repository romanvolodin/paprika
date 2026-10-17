from typing import override

from dmr.security.jwt.auth import CookieJWTSyncAuth
from dmr.security.jwt.blocklist import JWTokenBlocklistSyncMixin


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

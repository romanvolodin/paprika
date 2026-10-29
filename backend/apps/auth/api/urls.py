from dmr.routing import Router, path

from .views import (
    LoginController,
    LogoutController,
    PasswordController,
    RefreshController,
)


router = Router(
    "",
    [
        path("auth/login/", LoginController.as_view(), name="login"),
        path("auth/logout/", LogoutController.as_view(), name="logout"),
        path("auth/refresh/", RefreshController.as_view(), name="refresh"),
        path("auth/password/", PasswordController.as_view(), name="password"),
    ],
)

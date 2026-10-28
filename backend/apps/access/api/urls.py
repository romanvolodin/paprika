from dmr.routing import Router, path

from .views import (
    PermissionListController,
    RoleDetailController,
    RoleListController,
)


router = Router(
    "",
    [
        path(
            "permissions/",
            PermissionListController.as_view(),
            name="permission-list",
        ),
        path(
            "companies/<int:company_id>/roles/",
            RoleListController.as_view(),
            name="role-list",
        ),
        path(
            "roles/<int:role_id>/",
            RoleDetailController.as_view(),
            name="role-detail",
        ),
    ],
)

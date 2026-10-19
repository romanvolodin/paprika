from dmr.routing import Router, path

from .views import ProjectShotImportController


router = Router(
    "",
    [
        path(
            "projects/<int:project_id>/shot-imports/",
            ProjectShotImportController.as_view(),
            name="shot-import",
        ),
    ],
)

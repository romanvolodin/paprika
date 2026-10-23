from dmr.routing import Router, path

from .views import ProjectFeedController


router = Router(
    "",
    [
        path(
            "projects/<int:project_id>/feed/",
            ProjectFeedController.as_view(),
            name="project-feed",
        ),
    ],
)

from dmr.routing import Router, path

from .views import (
    ShotDetailController,
    ShotFiltersController,
    ShotGroupDetailController,
    ShotGroupListController,
    ShotGroupShotListController,
    ShotListController,
    ShotStatusDetailController,
    ShotStatusListController,
)


router = Router(
    "",
    [
        path(
            "projects/<int:project_id>/shot-groups/",
            ShotGroupListController.as_view(),
            name="shot-group-list",
        ),
        path(
            "shot-groups/<int:shot_group_id>/",
            ShotGroupDetailController.as_view(),
            name="shot-group-detail",
        ),
        path(
            "companies/<int:company_id>/shot-statuses/",
            ShotStatusListController.as_view(),
            name="shot-status-list",
        ),
        path(
            "shot-statuses/<int:shot_status_id>/",
            ShotStatusDetailController.as_view(),
            name="shot-status-detail",
        ),
        path(
            "projects/<int:project_id>/shots/",
            ShotListController.as_view(),
            name="shot-list",
        ),
        path(
            "projects/<int:project_id>/shot-filters/",
            ShotFiltersController.as_view(),
            name="shot-filters",
        ),
        path(
            "shot-groups/<int:shot_group_id>/shots/",
            ShotGroupShotListController.as_view(),
            name="shot-group-shot-list",
        ),
        path(
            "shots/<int:shot_id>/",
            ShotDetailController.as_view(),
            name="shot-detail",
        ),
    ],
)

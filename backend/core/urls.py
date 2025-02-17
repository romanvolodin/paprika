from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views


router = routers.DefaultRouter()
router.register("users", views.UserViewSet)
router.register("groups", views.GroupViewSet)

urlpatterns = [
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", views.CurrentUserView.as_view(), name="current_user"),
    path("api/", include(router.urls)),
    path("dj/api-auth/", include("rest_framework.urls", namespace="drf")),
    #
    path("dj/shots/from_xlsx/", views.read_xlsx),
    path("dj/shots/upload_previews/", views.save_multiple_uploaded_shot_previews),
    path(
        "dj/<str:project_code>/groups/",
        views.shot_group_list,
        name="shot_groups_list",
    ),
    path(
        "dj/<str:project_code>/groups/<int:shot_group_id>",
        views.shot_group_details,
        name="shot_group_details",
    ),
    path(
        "dj/<str:project_code>/tasks/",
        views.task_list,
        name="task_list",
    ),
    path(
        "dj/<str:project_code>/tasks/<int:task_id>",
        views.task_details,
        name="task_details",
    ),
    path(
        "dj/",
        views.project_list,
        name="project_list",
    ),
    path(
        "dj/<str:project_code>",
        views.project_details,
        name="project_details",
    ),
    path(
        "dj/versions/upload/",
        views.save_multiple_uploaded_versions,
        name="versions_upload",
    ),
    path("api/", views.api),
]

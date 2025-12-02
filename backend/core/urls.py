from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views
from .drf.urls import urlpatterns as drf_urlpatterns

router = routers.DefaultRouter()
router.register("users", views.UserViewSet)
router.register("groups", views.GroupViewSet)

router.register("projects", views.ProjectViewSet)
router.register("shot-groups", views.ShotGroupViewSet)
router.register("shot-tasks", views.ShotTaskViewSet)
router.register("tasks", views.TaskViewSet)
router.register("statuses", views.StatusViewSet)
router.register("versions", views.VersionViewSet)
router.register("chats", views.ChatViewSet)

urlpatterns = [
    path(
        "api/projects/<str:project_code>/shots/<str:shot_name>/",
        views.ShotViewSet.as_view({"get": "retrieve"}),
        name="shot-detail",
    ),
    path(
        "api/projects/<str:project_code>/shots/<str:shot_name>/versions/",
        views.VersionViewSet.as_view({"post": "create"}),
        name="create-shot-version",
    ),
    path(
        "api/projects/<str:project_code>/shots/<str:shot_name>/chat_messages/",
        views.ChatViewSet.as_view({"post": "create"}),
        name="chat-message-create",
    ),
    path(
        "api/projects/<str:project_code>/tasks/",
        views.TaskViewSet.as_view({"get": "list"}),
        name="tasks-by-project",
    ),
    path(
        "api/projects/<str:project_code>/tasks/<int:task_id>",
        views.TaskViewSet.as_view({"get": "retrieve"}),
        name="task-details-by-project",
    ),
    path(
        "api/projects/<str:project_code>/shot-groups/",
        views.ShotGroupViewSet.as_view({"get": "list"}),
        name="shot-groups-by-project",
    ),
    path(
        "api/projects/<str:project_code>/shot-groups/<int:shot_group_id>",
        views.ShotGroupViewSet.as_view({"get": "retrieve"}),
        name="shot-group-details-by-project",
    ),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", views.CurrentUserView.as_view(), name="current_user"),
    path("api/", include(router.urls)),
    path("dj/api-auth/", include("rest_framework.urls", namespace="drf")),
    #
    path("dj/shots/from_xlsx/", views.read_xlsx),
    path(
        "dj/versions/upload/",
        views.save_multiple_uploaded_versions,
        name="versions_upload",
    ),
]

urlpatterns += drf_urlpatterns

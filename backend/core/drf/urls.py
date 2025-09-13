from django.urls import path

from .views import create_shot_groups, create_shots


urlpatterns = [
    path(
        "api/projects/<str:project_code>/shots/create",
        create_shots,
        name="create-shots",
    ),
    path(
        "api/projects/<str:project_code>/shot-groups/create",
        create_shot_groups,
        name="create-shot-groups",
    ),
]

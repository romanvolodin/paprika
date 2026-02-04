from django.urls import path

from .views import create_shot_groups, create_shots, list_shots, list_shot_tasks


urlpatterns = [
    path(
        "api/projects/<str:project_code>/shots/create",
        create_shots,
        name="create-shots",
    ),
    path(
        "api/projects/<str:project_code>/shots2/",
        list_shots,
        name="list-shots",
    ),
    path(
        "api/projects/<str:project_code>/shot-groups/create",
        create_shot_groups,
        name="create-shot-groups",
    ),
    path(
        "api/projects/<str:project_code>/shots/<str:shot_name>/tasks/",
        list_shot_tasks,
        name="list-shot-tasks",
    ),
]

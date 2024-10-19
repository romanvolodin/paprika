from django.urls import path

from . import views


urlpatterns = [
    path("shots/from_xlsx/", views.read_xlsx),
    path("shots/upload_previews/", views.save_multiple_uploaded_shot_previews),
    path(
        "<str:project_code>/groups/",
        views.shot_group_list,
        name="shot_groups_list",
    ),
    path(
        "<str:project_code>/groups/<int:shot_group_id>",
        views.shot_group_details,
        name="shot_group_details",
    ),
    path(
        "<str:project_code>/tasks/",
        views.task_list,
        name="task_list",
    ),
    path(
        "<str:project_code>/tasks/<int:task_id>",
        views.task_details,
        name="task_details",
    ),
]

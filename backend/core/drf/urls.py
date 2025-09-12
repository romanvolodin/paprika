from django.urls import path

from .views import create_shots


urlpatterns = [
    path(
        "api/projects/<str:project_code>/shots/create",
        create_shots,
        name="create-shots",
    ),
]

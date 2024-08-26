from django.urls import path

from .views import read_xlsx, save_multiple_uploaded_shot_previews


urlpatterns = [
    path("shots/from_xlsx/", read_xlsx),
    path("shots/upload_previews/", save_multiple_uploaded_shot_previews),
]

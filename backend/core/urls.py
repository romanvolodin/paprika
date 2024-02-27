from django.urls import path

from .views import read_xlsx


urlpatterns = [
    path("shots/from_xlsx/", read_xlsx),
]

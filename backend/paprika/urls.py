from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, ScalarView
from dmr.routing import Router

from apps.access.api.urls import router as access_router
from apps.auth.api.urls import router as auth_router
from apps.chat.api.urls import router as chat_router
from apps.companies.api.urls import router as companies_router
from apps.feed.api.urls import router as feed_router
from apps.invitations.api.urls import router as invitations_router
from apps.projects.api.urls import router as projects_router
from apps.shot_import.api.urls import router as shot_import_router
from apps.shots.api.urls import router as shots_router
from apps.tasks.api.urls import router as tasks_router
from apps.users.api.urls import router as users_router
from apps.versions.api.urls import router as versions_router


api_router = Router("api/v1/")
api_router.include(access_router)
api_router.include(auth_router)
api_router.include(invitations_router)
api_router.include(chat_router)
api_router.include(companies_router)
api_router.include(feed_router)
api_router.include(projects_router)
api_router.include(shot_import_router)
api_router.include(shots_router)
api_router.include(tasks_router)
api_router.include(users_router)
api_router.include(versions_router)

schema = build_schema(api_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    api_router.to_urlpatterns(namespace="api"),
    path(
        "api/v1/docs/openapi.json",
        OpenAPIJsonView.as_view(schema),
        name="openapi",
    ),
    path("api/v1/docs/", ScalarView.as_view(schema), name="scalar"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

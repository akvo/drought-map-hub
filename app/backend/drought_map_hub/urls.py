from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from utils.modules import module_enabled

urlpatterns = [
    path("api/", include("api.v1.v1_init.urls"), name="v1_init"),
    path("api/", include("api.v1.v1_jobs.urls"), name="v1_jobs"),
    path("api/", include("api.v1.v1_users.urls"), name="v1_users"),
    path("api/", include("api.v1.v1_publication.urls"), name="v1_publication"),
    path("api/", include("api.v1.v1_rundeck.urls"), name="v1_rundeck"),
    path("api/", include("api.v1.v1_setup.urls"), name="v1_setup"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("admin/", admin.site.urls),
]

# DIH-1: the GeoNode push/read endpoints are wired only when the module is
# enabled (DIH-2). Off -> the routes are absent -> 404.
if module_enabled("geonode"):
    urlpatterns.insert(
        6, path("api/", include("api.v1.v1_geonode.urls"), name="v1_geonode")
    )

# DIH-7: the read-only client-data endpoints are wired only when the
# ``datasets`` module is enabled. Off -> the routes are absent -> 404.
if module_enabled("datasets"):
    urlpatterns.insert(
        6, path("api/", include("api.v1.v1_datasets.urls"), name="v1_datasets")
    )

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

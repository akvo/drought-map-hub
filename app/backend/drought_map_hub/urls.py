from django.urls import path, include
from django.contrib import admin
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("api/", include("api.v1.v1_init.urls"), name="v1_init"),
    path("api/", include("api.v1.v1_jobs.urls"), name="v1_jobs"),
    path("api/", include("api.v1.v1_users.urls"), name="v1_users"),
    path("api/", include("api.v1.v1_publication.urls"), name="v1_publication"),
    path("api/", include("api.v1.v1_rundeck.urls"), name="v1_rundeck"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("admin/", admin.site.urls),
]

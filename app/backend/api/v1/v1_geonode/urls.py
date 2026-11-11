from django.urls import re_path

from api.v1.v1_geonode.views import (
    CDIGeonodeAPI,
    GeonodePublicationPushAPI,
    GeonodeRasterPushAPI,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/admin/cdi-geonode",
        CDIGeonodeAPI.as_view(),
        name="cdi-geonode",
    ),
    re_path(
        r"^(?P<version>(v1))/geonode/publications$",
        GeonodePublicationPushAPI.as_view(),
        name="geonode-publication-push",
    ),
    re_path(
        r"^(?P<version>(v1))/geonode/publications/(?P<pk>[0-9]+)/rasters$",
        GeonodeRasterPushAPI.as_view(),
        name="geonode-raster-push",
    ),
]

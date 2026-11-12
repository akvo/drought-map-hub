from django.urls import re_path

from api.v1.v1_geonode.views import GeonodePublicationPushAPI

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/geonode/publications$",
        GeonodePublicationPushAPI.as_view(),
        name="geonode-publication-push",
    ),
]

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.v1.v1_publication.models import Raster
from api.v1.v1_geonode.models import GeoNodeResource
from api.v1.v1_geonode.serializers import (
    PushGeonodePublicationSerializer,
    PushGeonodePublicationResponseSerializer,
)
from utils.custom_permissions import HasApiKey
from utils.default_serializers import DefaultResponseSerializer


class GeonodePublicationPushAPI(APIView):
    """Attach GeoNode location pointers to a raster asset (DIH-1).

    Key-only (HasApiKey). Upserts the ``GeoNodeResource`` pointer row for the
    raster identified by ``geonode_id``, ensuring the core ``Raster`` exists
    first (the pipeline also pushes it to POST /api/v1/rasters; creating it
    here keeps the two pushes order-independent).
    """

    authentication_classes = []
    permission_classes = [HasApiKey]

    @extend_schema(
        summary="Push GeoNode resource pointers for a raster",
        tags=["Pipeline"],
        auth=[{"ApiKeyAuth": []}],
        request=PushGeonodePublicationSerializer,
        responses={
            200: PushGeonodePublicationResponseSerializer,
            201: PushGeonodePublicationResponseSerializer,
            403: DefaultResponseSerializer,
        },
    )
    def post(self, request, version):
        serializer = PushGeonodePublicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        raster, _ = Raster.objects.get_or_create(
            geonode_id=d["geonode_id"],
            defaults={
                "category": d["category"],
                "title": d["title"],
                "year_month": d["year_month"],
            },
        )
        resource, created = GeoNodeResource.objects.update_or_create(
            raster=raster,
            defaults={
                "detail_url": d.get("detail_url"),
                "embed_url": d.get("embed_url"),
                "thumbnail_url": d.get("thumbnail_url"),
                "download_url": d.get("download_url"),
                "file_size": d.get("file_size"),
            },
        )
        http_status = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return Response(
            {
                "geonode_id": raster.geonode_id,
                "synced_at": resource.synced_at,
            },
            status=http_status,
        )

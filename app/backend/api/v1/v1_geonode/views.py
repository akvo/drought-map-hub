from math import ceil

from django.utils import timezone
from rest_framework import status, serializers
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiParameter,
)

from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    PublicationStatus,
)
from api.v1.v1_geonode.models import PublicationGeonode, PublicationRaster
from api.v1.v1_geonode.serializers import (
    PushGeonodePublicationSerializer,
    PushGeonodeRasterSerializer,
    PushGeonodePublicationResponseSerializer,
    PushGeonodeRasterResponseSerializer,
    CDIGeonodeFilterSerializer,
    CDIGeonodeListSerializer,
)
from utils.custom_permissions import HasApiKey, IsAdmin
from utils.default_serializers import DefaultResponseSerializer


class GeonodePublicationPushAPI(APIView):
    """Steady-state metadata sync from the CDI pipeline into the cache."""

    # Key-only (no JWT): a missing/invalid key is a 403, not a 401.
    authentication_classes = []
    permission_classes = [HasApiKey]

    @extend_schema(
        summary="Push GeoNode publication metadata to cache",
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
        obj, created = PublicationGeonode.objects.update_or_create(
            geonode_id=d["geonode_id"],
            defaults={
                "category": d["category"],
                "title": d["title"],
                "year_month": d["year_month"],
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
            {"geonode_id": obj.geonode_id, "synced_at": obj.synced_at},
            status=http_status,
        )


class GeonodeRasterPushAPI(APIView):
    """GeoNode-down fallback: pre-computed raster values per indicator."""

    # Key-only (no JWT): a missing/invalid key is a 403, not a 401.
    authentication_classes = []
    permission_classes = [HasApiKey]

    @extend_schema(
        summary="Push pre-computed raster values (GeoNode-down fallback)",
        tags=["Pipeline"],
        auth=[{"ApiKeyAuth": []}],
        request=PushGeonodeRasterSerializer,
        responses={
            201: PushGeonodeRasterResponseSerializer,
            400: DefaultResponseSerializer,
            403: DefaultResponseSerializer,
            404: DefaultResponseSerializer,
        },
    )
    def post(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        serializer = PushGeonodeRasterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        now = timezone.now()
        raster, created = PublicationRaster.objects.update_or_create(
            publication=publication,
            indicator=d["indicator"],
            defaults={
                "geonode_id": d["geonode_id"],
                "values": d["values"],
                "extracted_at": now,
            },
        )
        http_status = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return Response(
            {
                "id": raster.id,
                "indicator": raster.indicator,
                "geonode_id": raster.geonode_id,
                "extracted_at": raster.extracted_at,
            },
            status=http_status,
        )


def _serialize_row(gn, pub):
    """Shape one cached GeoNode row into the list/detail item. A started
    publication overrides year_month/status; otherwise the cache stands."""
    return {
        "pk": gn.geonode_id,
        "title": gn.title,
        "detail_url": gn.detail_url,
        "embed_url": gn.embed_url,
        "thumbnail_url": gn.thumbnail_url,
        "download_url": gn.download_url,
        "created": gn.resource_created,
        "year_month": pub["year_month"] if pub else gn.year_month,
        "publication_id": pub["id"] if pub else None,
        "status": pub["status"] if pub else None,
    }


class CDIGeonodeAPI(APIView):
    """Admin publication picker, served from the PublicationGeonode cache so
    reads never depend on GeoNode being reachable (DIH-1). The cache is kept
    warm by the pipeline push and sync_publication_geonodes."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch CDI Geonode resources",
        description=(
            "Fetch cached geodata resources from a specific category "
            "to start publication process"
        ),
        tags=["Admin"],
        parameters=[
            OpenApiParameter(
                name="page",
                default=1,
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="category",
                default=CDIGeonodeCategory.cdi,
                required=False,
                enum=CDIGeonodeCategory.FieldStr.keys(),
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="status",
                required=False,
                enum=PublicationStatus.FieldStr.keys(),
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="id",
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
        ],
        request=CDIGeonodeFilterSerializer,
        responses={
            200: CDIGeonodeListSerializer(many=True),
            (200, "application/json"): inline_serializer(
                "CDIGeonodeListResponse",
                fields={
                    "current": serializers.IntegerField(),
                    "total": serializers.IntegerField(),
                    "total_page": serializers.IntegerField(),
                    "data": CDIGeonodeListSerializer(many=True),
                },
            ),
            400: DefaultResponseSerializer,
            500: DefaultResponseSerializer,
        },
    )
    def get(self, request, *args, **kwargs):
        serializer = CDIGeonodeFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            raise ValidationError({
                "message": "Invalid category parameter."
            })

        # Single-resource lookup by GeoNode id.
        if serializer.validated_data.get("id"):
            cdi_id = serializer.validated_data["id"]
            gn = PublicationGeonode.objects.filter(geonode_id=cdi_id).first()
            if not gn:
                return Response(
                    {"message": "Server Error: Unable to fetch data."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            publication = Publication.objects.filter(
                cdi_geonode_id=cdi_id
            ).first()
            pub = {
                "id": publication.pk,
                "status": publication.status,
                "year_month": publication.year_month,
            } if publication else None
            return Response(
                CDIGeonodeListSerializer(
                    instance=_serialize_row(gn, pub)
                ).data,
                status=status.HTTP_200_OK,
            )

        # List lookup by category (+ optional publication status filter).
        category = serializer.validated_data.get(
            "category", CDIGeonodeCategory.cdi
        )
        publication_status = serializer.validated_data.get("status")
        page = int(request.GET.get("page", "1"))
        page_size = 10

        qs = PublicationGeonode.objects.filter(
            category=category
        ).order_by("-year_month")
        if publication_status is not None:
            matching_ids = Publication.objects.filter(
                status=publication_status
            ).values_list("cdi_geonode_id", flat=True)
            qs = qs.filter(geonode_id__in=matching_ids)

        rows = list(qs)
        publications_dict = {
            pub.cdi_geonode_id: {
                "id": pub.pk,
                "status": pub.status,
                "year_month": pub.year_month,
            }
            for pub in Publication.objects.filter(
                cdi_geonode_id__in=[gn.geonode_id for gn in rows]
            )
        }
        items = [
            _serialize_row(gn, publications_dict.get(gn.geonode_id))
            for gn in rows
        ]

        total = len(items)
        total_page = ceil(total / page_size) if total else 0
        start = (page - 1) * page_size
        page_items = items[start:start + page_size]
        return Response(
            {
                "current": page,
                "total": total,
                "total_page": total_page,
                "data": CDIGeonodeListSerializer(
                    instance=page_items, many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )

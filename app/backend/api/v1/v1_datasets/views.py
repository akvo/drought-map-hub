"""Read-only, public client-data API (DIH-7).

Public like the rest of Insights; no upload endpoint. Wired only when the
``datasets`` module is enabled (see drought_map_hub/urls.py) — off -> 404.
"""

from datetime import datetime

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_datasets.metadata import dataset_meta
from api.v1.v1_datasets.models import AdminDatasetValue
from api.v1.v1_datasets.serializers import (
    DatasetPeriodsSerializer,
    DatasetResponseSerializer,
)


def _periods_qs(key: str):
    return (
        AdminDatasetValue.objects.filter(dataset=key)
        .values_list("period", flat=True)
        .distinct()
        .order_by("period")
    )


class AdminDatasetAPI(APIView):
    """One dataset for one month as a map/table payload (house contract)."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Get a client dataset for a period",
        tags=["Datasets"],
        parameters=[
            OpenApiParameter(
                name="period",
                required=False,
                description="YYYY-MM; defaults to the latest available period",
            )
        ],
        responses={200: DatasetResponseSerializer},
    )
    def get(self, request, version, key):
        raw_period = request.query_params.get("period")
        if raw_period:
            try:
                parsed = datetime.strptime(raw_period, "%Y-%m").date()
                period = parsed.replace(day=1)
            except ValueError:
                return Response(
                    {"message": "period must be YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            period = _periods_qs(key).last()

        meta = dataset_meta(key)
        data = [
            {"administration_id": adm_id, "value": value}
            for adm_id, value in AdminDatasetValue.objects.filter(
                dataset=key, period=period
            )
            .order_by("administration_id")
            .values_list("administration_id", "value")
        ]
        return Response(
            {
                "meta": {
                    "key": key,
                    "label": meta["label"],
                    "unit": meta["unit"],
                    "period": period.strftime("%Y-%m") if period else None,
                },
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDatasetPeriodsAPI(APIView):
    """Available periods for a dataset key (ascending)."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="List available periods for a dataset",
        tags=["Datasets"],
        responses={200: DatasetPeriodsSerializer},
    )
    def get(self, request, version, key):
        periods = [p.strftime("%Y-%m") for p in _periods_qs(key)]
        return Response(
            {"key": key, "periods": periods},
            status=status.HTTP_200_OK,
        )

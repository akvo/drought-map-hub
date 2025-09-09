from rest_framework import status
from rest_framework.decorators import (
    api_view,
)
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from utils.default_serializers import DefaultResponseSerializer


@extend_schema(
    description="Use to check System health",
    tags=["Dev"],
    responses=DefaultResponseSerializer,
)
@api_view(["GET"])
def health_check(request, version):
    return Response(  # pragma: no cover
        {"message": "OK"},
        status=status.HTTP_200_OK
    )

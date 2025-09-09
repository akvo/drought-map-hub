import requests
from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiParameter,
)
from django.conf import settings
from utils.custom_permissions import IsAdmin
from api.v1.v1_rundeck.models import Settings
from api.v1.v1_rundeck.serializers import (
    SettingsSerializer,
    UpdateSettingsSerializer,
    RundeckProjectSerializer,
    RundeckJobSerializer,
    RundeckExecutionJobSerializer,
    RundeckJobOptionsSerializer,
    ContactsSerializer,
)
from api.v1.v1_rundeck.constants import RundeckJobStatus
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from utils.custom_serializer_fields import validate_serializers_message
from utils.rundeck_config import rundeck_set_notification


class RundeckAPIError(Exception):
    """Custom exception for third-party API failures."""
    def __init__(self, message, status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@extend_schema(
    responses={200: SettingsSerializer},
    tags=["Admin"],
    description="Manage Rundeck settings",
)
class SettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Settings.
    Only authenticated admin users have access.
    """
    queryset = Settings.objects.all()
    serializer_class = SettingsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action == "update":
            return UpdateSettingsSerializer
        return SettingsSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            self.perform_update(serializer)
        except RundeckAPIError as e:
            return Response(
                {"message": e.message},
                status=e.status_code or status.HTTP_502_BAD_GATEWAY
            )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        try:
            instance = serializer.save()
            api_url = (
                f"{settings.RUNDECK_API_URL}/project/"
                f"{instance.project_name}/jobs/export"
            )
            response = requests.get(
                    api_url,
                    headers={
                        "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                    }
                )
            response.raise_for_status()
            if response.status_code == 200:
                configs = response.json()
                configs = list(filter(
                    lambda x: x["id"] == f"{instance.job_id}",
                    configs
                ))
                config = configs[0] \
                    if len(configs) > 0 else instance.job_config
                if config:
                    instance.job_config = config
                    instance.save()
                    config = rundeck_set_notification(
                        config=config,
                        on_success_emails=instance.on_success_emails,
                        on_failure_emails=instance.on_failure_emails,
                        on_exceeded_emails=instance.on_exceeded_emails,
                    )
                    requests.delete(
                        f"{settings.RUNDECK_API_URL}/job/{instance.job_id}",
                        headers={
                            "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                        }
                    )
                    import_api_url = (
                        f"{settings.RUNDECK_API_URL}/project/"
                        f"{instance.project_name}/jobs/import"
                    )
                    response = requests.post(
                        import_api_url,
                        json=[config],
                        headers={
                            "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                        }
                    )
                    response.raise_for_status()
        except requests.RequestException as e:
            raise RundeckAPIError(
                str(e),
                status.HTTP_502_BAD_GATEWAY
            )


class RundeckProjectsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch Rundeck Projects",
        tags=["Rundeck"],
        responses=RundeckProjectSerializer,
    )
    def get(self, request, *args, **kwargs):
        try:
            response = requests.get(
                f"{settings.RUNDECK_API_URL}/projects",
                headers={
                    "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                }
            )
            data = response.json()
            if response.status_code == 200 and data:
                return Response(
                    RundeckProjectSerializer(
                        instance=data,
                        many=True
                    ).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    response.json(),
                    status=response.status_code,
                )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RundeckJobsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch Rundeck Projects",
        tags=["Rundeck"],
        responses=RundeckJobSerializer,
    )
    def get(self, request, version, project):
        try:
            response = requests.get(
                f"{settings.RUNDECK_API_URL}/project/{project}/jobs",
                headers={
                    "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                }
            )
            data = response.json()
            if response.status_code == 200 and data:
                return Response(
                    RundeckJobSerializer(
                        instance=data,
                        many=True
                    ).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    response.json(),
                    status=response.status_code,
                )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminContactView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Get a list of Admin contacts",
        tags=["Admin"],
        responses=ContactsSerializer,
    )
    def get(self, request, version):
        users = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).all()
        contacts = [
            u.email
            for u in users
        ]
        return Response(
            {
                "contacts": contacts
            },
            status=status.HTTP_200_OK
        )


class RundeckExecutionsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch Job Executions",
        tags=["Rundeck"],
        parameters=[
            OpenApiParameter(
                name="page",
                default=1,
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="status",
                default=None,
                required=False,
                enum=RundeckJobStatus.FieldStr.keys(),
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            (200, "application/json"): inline_serializer(
                "DataList",
                fields={
                    "current": serializers.IntegerField(),
                    "total": serializers.IntegerField(),
                    "total_page": serializers.IntegerField(),
                    "data": RundeckExecutionJobSerializer(many=True),
                },
            )
        },
    )
    def get(self, request, version, job_id):
        try:
            page = int(request.GET.get("page", "1"))
            page = page - 1
            api_url = (
                f"{settings.RUNDECK_API_URL}/job/{job_id}/executions"
                f"?offset={page}"
            )
            job_status = request.GET.get("status", None)
            if job_status:
                api_url = f"{api_url}&status={job_status}"
            response = requests.get(
                api_url,
                headers={
                    "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                }
            )
            data = response.json()
            return Response(
                {
                    "current": page,
                    "total": data["paging"]["total"],
                    "total_page": data["paging"]["max"],
                    "data": RundeckExecutionJobSerializer(
                        instance=data["executions"],
                        many=True
                    ).data
                },
                status=response.status_code,
            )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Run Job",
        tags=["Rundeck"],
        request=RundeckJobOptionsSerializer,
        responses=RundeckExecutionJobSerializer,
    )
    def post(self, request, version, job_id):
        try:
            serializer = RundeckJobOptionsSerializer(
                data=request.data
            )
            if not serializer.is_valid():
                return Response(
                    {
                        "message": validate_serializers_message(
                            serializer.errors
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            response = requests.post(
                f"{settings.RUNDECK_API_URL}/job/{job_id}/run",
                json={
                    "options": {
                        "year_month": serializer.validated_data["year_month"],
                        "lst_weight": str(
                            serializer.validated_data["lst_weight"]
                        ),
                        "ndvi_weight": str(
                            serializer.validated_data["ndvi_weight"]
                        ),
                        "spi_weight": str(
                            serializer.validated_data["spi_weight"]
                        ),
                        "sm_weight": str(
                            serializer.validated_data["sm_weight"]
                        ),
                    }
                },
                headers={
                    "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                }
            )
            return Response(
                response.json(),
                status=response.status_code,
            )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

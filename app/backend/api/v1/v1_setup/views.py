import json
from django.conf import settings
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from api.v1.v1_setup.models import SiteConfig, Organization
from api.v1.v1_setup.serializers import (
    SetupSerializer,
    SetupResponseSerializer,
    OrganizationSerializer,
    BoundingBoxSerializer,
    BoundingBoxResponseSerializer,
    InitialUserSerializer,
    InitialUserResponseSerializer,
)
from utils.custom_permissions import IsAdmin


class SetupView(APIView):
    """
    Unified view to manage the application setup.
    POST: Initial setup of the application with site configuration and
          organizations.
    GET: Retrieve current site configuration and organizations.
    PUT: Update site configuration and organizations.
    """
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={201: SetupResponseSerializer},
        request=inline_serializer(
            name="SetupRequest",
            fields={
                'name': serializers.CharField(help_text="Site name"),
                'geojson_file': serializers.FileField(
                    help_text="GeoJSON file"
                ),
                'organizations[0][name]': serializers.CharField(
                    help_text="Organization name"
                ),
                'organizations[0][website]': serializers.CharField(
                    required=False, help_text="Organization website"
                ),
                'organizations[0][is_twg]': serializers.BooleanField(
                    required=False, help_text="Is TWG organization"
                ),
                'organizations[0][is_collaborator]': serializers.BooleanField(
                    required=False, help_text="Is collaborator organization"
                ),
                'organizations[0][logo]': serializers.FileField(
                    required=False, help_text="Organization logo"
                ),
            }
        ),
        tags=["Setup"],
        description=(
            "Setup the application with site configuration and organizations. "
            "For multiple organizations, use organizations[1][name], "
            "organizations[1][website], etc."
        ),
    )
    def post(self, request, *args, **kwargs):
        """
        Initial setup of the application with site configuration and
        organizations. Processes uploaded GeoJSON file and converts it to
        TopoJSON.
        """
        # Check if setup has already been completed
        if SiteConfig.objects.exists():
            return Response(
                {
                    "error": (
                        "Setup has already been completed. "
                        "Cannot reconfigure."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SetupSerializer(data=request.data)

        if serializer.is_valid():
            site_config = serializer.save()

            # Prepare response data manually instead of using response
            # serializer
            organizations_data = []
            if hasattr(site_config, 'created_organizations'):
                organizations_data = OrganizationSerializer(
                    site_config.created_organizations,
                    many=True
                ).data
            response_data = SetupResponseSerializer(site_config).data
            response_data['organizations'] = organizations_data

            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={200: SetupResponseSerializer},
        tags=["Setup"],
        description=(
            "Retrieve the current site configuration and organizations."
        ),
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve current site configuration and organizations.
        """
        site_config = SiteConfig.objects.first()
        if not site_config:
            return Response(
                {"error": "Site configuration not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        # Get all organizations
        organizations = Organization.objects.all()
        organizations_data = OrganizationSerializer(
            organizations, many=True
        ).data
        response_data = SetupResponseSerializer(site_config).data
        response_data['organizations'] = organizations_data
        return Response(response_data, status=status.HTTP_200_OK)


class ManageSetupView(APIView):
    """
    PUT: Update specific site configuration by ID.
    """

    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=inline_serializer(
            name="UpdateSetupByIDRequest",
            fields={
                'name': serializers.CharField(help_text="Site name"),
                'geojson_file': serializers.FileField(
                    help_text="GeoJSON file", required=False
                ),
                'organizations[0][name]': serializers.CharField(
                    help_text="Organization name"
                ),
                'organizations[0][website]': serializers.CharField(
                    required=False, help_text="Organization website"
                ),
                'organizations[0][is_twg]': serializers.BooleanField(
                    required=False, help_text="Is TWG organization"
                ),
                'organizations[0][is_collaborator]': serializers.BooleanField(
                    required=False, help_text="Is collaborator organization"
                ),
                'organizations[0][logo]': serializers.FileField(
                    required=False, help_text="Organization logo"
                ),
            }
        ),
        responses={200: SetupResponseSerializer},
        tags=["Setup"],
        description="Update the site configuration and organizations by ID.",
    )
    def put(self, request, *args, **kwargs):
        """
        Update specific site configuration by ID.
        """
        uuid = kwargs.get('uuid')
        site_config = get_object_or_404(SiteConfig, uuid=uuid)

        serializer = SetupSerializer(
            site_config,
            data=request.data,
            partial=True
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        site_config = serializer.save()

        # Get all organizations
        organizations = Organization.objects.all()
        organizations_data = OrganizationSerializer(
            organizations, many=True
        ).data

        response_data = {
            'id': site_config.id,
            'name': site_config.name,
            'organizations': organizations_data,
            'created_at': site_config.created_at,
            'updated_at': site_config.updated_at,
        }
        return Response(response_data, status=status.HTTP_200_OK)


def to_bool(value):
    return str(value).lower() in ['true', '1']


class OrganizationViewSet(ModelViewSet):
    """
    ViewSet for managing organizations.
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Organizations"],
        description="List all organizations.",
        parameters=[
            inline_serializer(
                name="OrganizationListParams",
                fields={
                    'search': serializers.CharField(
                        help_text="Search organizations by name",
                        required=False
                    ),
                    'is_twg': serializers.BooleanField(
                        help_text="Filter by TWG organizations",
                        required=False
                    ),
                    'is_collaborator': serializers.BooleanField(
                        help_text="Filter by collaborator organizations",
                        required=False
                    ),
                }
            )
        ],
        responses={200: OrganizationSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        is_twg = request.query_params.get('is_twg')
        if is_twg is not None:
            self.queryset = self.queryset.filter(is_twg=to_bool(is_twg))

        is_collaborator = request.query_params.get('is_collaborator')
        if is_collaborator is not None:
            self.queryset = self.queryset.filter(
                is_collaborator=to_bool(is_collaborator)
            )

        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Organizations"],
        description="Create a new organization.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["Organizations"],
        description="Retrieve an organization by ID.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Organizations"],
        description="Update an organization by ID.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["Organizations"],
        description="Partially update an organization by ID.",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=["Organizations"],
        description="Delete an organization by ID.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class BoundingBoxView(APIView):
    @extend_schema(
        responses={200: BoundingBoxResponseSerializer},
        tags=["Setup"],
        description="Retrieve the current bounding box.",
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve the current bounding box from
        ./source/config/cdi_project_settings.json
        """
        try:
            with open(
                'backend/source/config/cdi_project_settings.json', 'r'
            ) as f:
                config = json.load(f)
                bbox = config.get('bounds', {})
        except (FileNotFoundError, json.JSONDecodeError):
            bbox = {
                "n_lat": 0.0,
                "s_lat": 0.0,
                "w_lon": 0.0,
                "e_lon": 0.0
            }

        return Response(
            {
                'bounding_box': bbox,
                'message': 'Bounding box retrieved successfully.'
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        request=BoundingBoxSerializer,
        responses={200: BoundingBoxResponseSerializer},
        tags=["Setup"],
        description="Update the bounding box.",
    )
    def post(self, request, *args, **kwargs):
        """
        Update the bounding box in ./source/config/cdi_project_settings.json.
        """
        serializer = BoundingBoxSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        bbox = serializer.validated_data
        try:
            with open(
                './source/config/cdi_project_settings.template.json', 'r+'
            ) as f:
                config = json.load(f)
                config['bounds'] = {
                    'n_lat': bbox['n_lat'],
                    's_lat': bbox['s_lat'],
                    'w_lon': bbox['w_lon'],
                    'e_lon': bbox['e_lon'],
                }
                f.seek(0)
                json.dump(config, f, indent=2)
                f.truncate()
                json_file = "cdi_project_settings.json"
                if settings.TEST_ENV:
                    json_file = f"{json_file}".replace(
                        ".json", ".test.json"
                    )
                with open(
                    f'./source/config/{json_file}', 'w'
                ) as json_file:
                    json.dump(config, json_file, indent=2)
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            return Response(
                {'error': f'Failed to update configuration: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(
            {
                'bounding_box': config['bounds'],
                'message': 'Bounding box updated successfully.'
            },
            status=status.HTTP_200_OK
        )


class UserSetupView(APIView):
    """
    GET: Check if the setup has been completed.
    POST: Create the initial admin user and reviewer Email list.
    """

    @extend_schema(
        responses={
            200: inline_serializer(
                name="SetupStatusResponse",
                fields={
                    'is_configured': serializers.BooleanField(
                        help_text="Indicates if setup is complete"
                    )
                }
            )
        },
        tags=["Setup"],
        description="Check if the setup has been completed.",
    )
    def get(self, request, *args, **kwargs):
        """
        Check if the setup has been completed.
        """
        is_configured = SiteConfig.objects.exists()
        return Response(
            {'is_configured': is_configured},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        request=InitialUserSerializer,
        responses={201: InitialUserResponseSerializer},
        tags=["Setup"],
        description="Create the initial admin user and reviewer Email list.",
    )
    def post(self, request, *args, **kwargs):
        """
        Create the initial admin user and reviewer Email list.
        """
        serializer = InitialUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            reviewers = serializer.validated_data.get('reviewers', [])
            response_data = InitialUserResponseSerializer(user).data
            response_data['reviewers'] = reviewers
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

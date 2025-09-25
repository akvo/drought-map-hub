import json
import os
import shutil
from django.conf import settings
from django.core.management import call_command
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
    CountrySerializer,
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
            # After successful setup, run the roles and abilities seeder
            call_command("generate_roles_n_abilities_seeder")
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


# Align bounds to HDF grid system (0.05-degree spacing)
# HDF grid: longitude starts at -179.975°, latitude starts at 89.975°
def align_to_hdf_grid(value, is_longitude=True, is_upper_bound=True):
    """
    Align coordinate to HDF grid system.
    HDF uses 0.05° spacing:
    - Longitude: -179.975, -179.925, -179.875, ...
    - Latitude: 89.975, 89.925, 89.875, ...
    """
    if is_longitude:
        # For longitude: base is -179.975
        base = -179.975
    else:
        # For latitude: base is 89.975, descending values
        base = 89.975
    # Calculate grid index
    if is_longitude:
        grid_index = round((value - base) / 0.05)
    else:
        # For latitude, calculate from the top (89.975)
        grid_index = round((base - value) / 0.05)
    # Calculate aligned value
    if is_longitude:
        aligned = base + (grid_index * 0.05)
    else:
        aligned = base - (grid_index * 0.05)
    # For bounds expansion, move to next grid point if needed
    if is_upper_bound:
        if is_longitude and aligned < value:
            aligned += 0.05
        elif not is_longitude and aligned < value:
            aligned -= 0.05
    else:
        if is_longitude and aligned > value:
            aligned -= 0.05
        elif not is_longitude and aligned > value:
            aligned += 0.05
    return round(aligned, 3)


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
        config_file = 'cdi_project_settings.json'
        if settings.TEST_ENV:
            config_file = 'cdi_project_settings.test.json'
        config_path = f'./source/config/{config_file}'
        try:
            with open(config_path, 'r') as f:
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
        Update the bounding box using the improved BoundingBoxSerializer.
        """
        serializer = BoundingBoxSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        # Path to the CDI project settings files
        template_path = './source/config/cdi_project_settings.template.json'
        config_path = './source/config/cdi_project_settings.json'
        if settings.TEST_ENV:
            config_path = './source/config/cdi_project_settings.test.json'
        # If main config doesn't exist, copy from template
        if not os.path.exists(config_path):
            # Copy template to create main config file
            shutil.copy2(template_path, config_path)
        # Read the config file (now guaranteed to exist)
        with open(config_path, 'r') as f:
            config = json.load(f)
        bounds_data = serializer.validated_data
        # Align bounds to HDF grid and expand slightly for coverage
        aligned_bounds = {
            "n_lat": align_to_hdf_grid(
                float(bounds_data["n_lat"]),
                is_longitude=False,
                is_upper_bound=True
            ),
            "s_lat": align_to_hdf_grid(
                float(bounds_data["s_lat"]),
                is_longitude=False,
                is_upper_bound=False
            ),
            "w_lon": align_to_hdf_grid(
                float(bounds_data["w_lon"]),
                is_longitude=True,
                is_upper_bound=False
            ),
            "e_lon": align_to_hdf_grid(
                float(bounds_data["e_lon"]),
                is_longitude=True,
                is_upper_bound=True
            )
        }
        config['bounds'] = aligned_bounds
        # Update region name if provided
        site_config = SiteConfig.objects.first()
        if site_config and site_config.country:
            config['region_name'] = site_config.country
        # Write updated config back to main file (not template)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        updated_bounds = config['bounds']
        return Response(
            {
                'bounding_box': updated_bounds,
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


class CountryListView(APIView):
    """
    GET: Retrieve the list of countries from countries.json.
    """

    @extend_schema(
        responses={200: CountrySerializer(many=True)},
        tags=["Setup"],
        description="Retrieve the list of countries from countries.json.",
    )
    def get(self, request, *args, **kwargs):
        countries_file = os.path.join(
            settings.BASE_DIR,
            'source',
            'countries.json'
        )
        try:
            with open(countries_file, 'r') as f:
                countries = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            countries = []
        return Response(
            data=CountrySerializer(countries, many=True).data,
            status=status.HTTP_200_OK
        )

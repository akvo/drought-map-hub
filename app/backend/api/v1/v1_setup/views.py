
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from api.v1.v1_setup.models import SiteConfig, Organization
from api.v1.v1_setup.serializers import (
    SetupSerializer, SetupResponseSerializer, OrganizationSerializer
)


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
                for org in site_config.created_organizations:
                    org_data = {
                        'id': org.id,
                        'name': org.name,
                        'website': org.website,
                        'logo': org.logo.url if org.logo else None,
                        'is_twg': org.is_twg,
                        'is_collaborator': org.is_collaborator,
                        'created_at': org.created_at,
                        'updated_at': org.updated_at,
                    }
                    organizations_data.append(org_data)
            response_data = {
                'id': site_config.id,
                'name': site_config.name,
                'topojson_file': getattr(site_config, 'topojson_path', ''),
                'organizations': organizations_data,
                'message': 'Setup completed successfully.',
                'created_at': site_config.created_at,
                'updated_at': site_config.updated_at,
            }

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
        response_data = {
            'id': site_config.id,
            'name': site_config.name,
            'organizations': organizations_data,
            'created_at': site_config.created_at,
            'updated_at': site_config.updated_at,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @extend_schema(
        request=inline_serializer(
            name="UpdateSetupRequest",
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
        description="Update the site configuration and organizations.",
    )
    def put(self, request, *args, **kwargs):
        """
        Update site configuration and organizations.
        """
        # Get pk from kwargs if provided, otherwise get the first site config
        pk = kwargs.get('pk')
        if pk:
            site_config = get_object_or_404(SiteConfig, pk=pk)
        else:
            site_config = SiteConfig.objects.first()
            if not site_config:
                return Response(
                    {"error": "Site configuration not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

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

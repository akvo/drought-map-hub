from rest_framework import serializers
from api.v1.v1_setup.models import SiteConfig, Organization
from utils.geojson_processor import process_geojson_file, validate_geojson_file
from uuid import uuid4


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'website',
            'logo',
            'is_twg',
            'is_collaborator',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SetupSerializer(serializers.ModelSerializer):
    organizations = OrganizationSerializer(many=True, write_only=True)
    geojson_file = serializers.FileField(write_only=True)

    class Meta:
        model = SiteConfig
        fields = [
            'id',
            'name',
            'geojson_file',
            'organizations',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Site name is required.")
        return value

    def validate_geojson_file(self, value):
        if not value:
            raise serializers.ValidationError(
                "GeoJSON file is required."
            )

        try:
            validate_geojson_file(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        return value

    def to_internal_value(self, data):
        """Override to handle multipart form data for nested organizations."""
        # Handle organizations field specially for multipart data
        if hasattr(data, 'get'):
            # For multipart form data, organizations come as individual fields
            organizations_data = []
            i = 0
            while True:
                name_key = f'organizations[{i}][name]'
                website_key = f'organizations[{i}][website]'
                is_twg_key = f'organizations[{i}][is_twg]'
                is_collab_key = f'organizations[{i}][is_collaborator]'
                logo_key = f'organizations[{i}][logo]'

                # Check if any organization field exists for this index
                org_field_exists = (
                    name_key in data or website_key in data or
                    is_twg_key in data or is_collab_key in data or
                    logo_key in data
                )

                if org_field_exists:
                    name_val = data.get(name_key)
                    website_val = data.get(website_key, '')
                    is_twg_val = data.get(is_twg_key)
                    is_collab_val = data.get(is_collab_key)

                    org_data = {
                        'name': name_val,
                        'website': website_val,
                        'is_twg': is_twg_val in ['true', 'True', '1', True],
                        'is_collaborator': is_collab_val in [
                            'true', 'True', '1', True
                        ],
                    }
                    if logo_key in data:
                        org_data['logo'] = data[logo_key]
                    organizations_data.append(org_data)
                    i += 1
                else:
                    break
            if organizations_data:
                # Create a mutable copy of data
                data_dict = dict(data.items())
                data_dict['organizations'] = organizations_data
                return super().to_internal_value(data_dict)
        return super().to_internal_value(data)

    def validate_organizations(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one organization is required."
            )
        return value

    def create(self, validated_data):
        # Extract the geojson_file and organizations data
        geojson_file = validated_data.pop('geojson_file')
        organizations_data = validated_data.pop('organizations')

        # Process the GeoJSON file and save it as TopoJSON
        try:
            topojson_path = process_geojson_file(geojson_file)
        except ValueError as e:
            raise serializers.ValidationError({
                'geojson_file': str(e)
            })

        # Create the SiteConfig (without the geojson_file field)
        validated_data['uuid'] = uuid4()
        site_config = SiteConfig.objects.create(**validated_data)

        # Create organizations
        created_organizations = []
        for org_data in organizations_data:
            organization = Organization.objects.create(**org_data)
            created_organizations.append(organization)

        # Add organizations and topojson path to the response data
        site_config.created_organizations = created_organizations
        site_config.topojson_path = topojson_path
        return site_config

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # Delete existing organizations
        Organization.objects.all().delete()

        # Create new organizations
        organizations_data = validated_data.get('organizations', [])
        created_organizations = []
        for org_data in organizations_data:
            organization = Organization.objects.create(**org_data)
            created_organizations.append(organization)

        instance.created_organizations = created_organizations

        # Extract geojson_file if provided
        geojson_file = validated_data.pop('geojson_file', None)
        if geojson_file:
            try:
                topojson_path = process_geojson_file(geojson_file)
                instance.topojson_path = topojson_path
            except ValueError as e:
                raise serializers.ValidationError({
                    'geojson_file': str(e)
                })

        return instance


class SetupResponseSerializer(serializers.ModelSerializer):
    organizations = OrganizationSerializer(many=True, read_only=True)
    message = serializers.CharField(read_only=True)
    topojson_file = serializers.CharField(read_only=True)

    class Meta:
        model = SiteConfig
        fields = [
            'uuid',
            'name',
            'topojson_file',
            'organizations',
            'message',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

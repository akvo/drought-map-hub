import os
from django_q.tasks import async_task
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from api.v1.v1_setup.models import SiteConfig, Organization
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_jobs.models import Jobs, JobTypes, JobStatus
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
            'uuid',
            'name',
            'geojson_file',
            'organizations',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

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
            process_geojson_file(geojson_file)
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

        # Add organizations and geojson path to the response data
        site_config.created_organizations = created_organizations
        site_config.geojson_file = geojson_file
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
                process_geojson_file(geojson_file)
                instance.geojson_file = geojson_file
                instance.save()
            except ValueError as e:
                raise serializers.ValidationError({
                    'geojson_file': str(e)
                })

        return instance


class SetupResponseSerializer(serializers.ModelSerializer):
    organizations = OrganizationSerializer(many=True, read_only=True)
    is_configured = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_configured(self, obj):
        config_exists = os.path.exists(
            './source/config/cdi_project_settings.json'
        )
        admin_exists = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).exists()
        if not admin_exists or not config_exists:
            return False
        return True

    class Meta:
        model = SiteConfig
        fields = [
            'uuid',
            'name',
            'geojson_file',
            'created_at',
            'updated_at',
            'is_configured',
            'organizations',
        ]


class BoundingBoxSerializer(serializers.Serializer):
    n_lat = serializers.FloatField()
    s_lat = serializers.FloatField()
    w_lon = serializers.FloatField()
    e_lon = serializers.FloatField()

    def validate(self, data):
        # Validate latitude ranges
        if not (-90 <= data['s_lat'] <= 90):
            raise serializers.ValidationError(
                "South latitude must be between -90 and 90."
            )
        if not (-90 <= data['n_lat'] <= 90):
            raise serializers.ValidationError(
                "North latitude must be between -90 and 90."
            )
        # Validate longitude ranges
        if not (-180 <= data['w_lon'] <= 180):
            raise serializers.ValidationError(
                "West longitude must be between -180 and 180."
            )
        if not (-180 <= data['e_lon'] <= 180):
            raise serializers.ValidationError(
                "East longitude must be between -180 and 180."
            )
        # Validate ordering
        if data['n_lat'] <= data['s_lat']:
            raise serializers.ValidationError(
                "North latitude must be greater than south latitude."
            )
        if data['e_lon'] <= data['w_lon']:
            raise serializers.ValidationError(
                "East longitude must be greater than west longitude."
            )
        return data

    class Meta:
        fields = ['n_lat', 's_lat', 'w_lon', 'e_lon']


class BoundingBoxResponseSerializer(serializers.Serializer):
    bounding_box = BoundingBoxSerializer(read_only=True)
    message = serializers.CharField(read_only=True)

    class Meta:
        fields = ['bounding_box', 'message']


class ReviewerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    organization_id = serializers.IntegerField()

    def validate_organization_id(self, value):
        if not Organization.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid organization ID.")
        return value

    def validate_email(self, value):
        if SystemUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    class Meta:
        fields = ['name', 'email', 'organization_id']


class InitialUserSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    reviewers = ReviewerSerializer(many=True, required=False)

    def validate_confirm_password(self, value):
        if 'password' in self.initial_data:
            if value != self.initial_data['password']:
                raise serializers.ValidationError(
                    "Password and confirm password do not match."
                )
        return value

    def validate_email(self, value):
        if SystemUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def create(self, validated_data):
        # Extract reviewers data if present
        reviewers_data = validated_data.pop('reviewers', [])
        # Create the initial admin user
        admin_user = SystemUser.objects.create_superuser(
            name=validated_data['name'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        # Send verification email to admin user
        job = Jobs.objects.create(
            type=JobTypes.verification_email,
            status=JobStatus.on_progress,
            result=admin_user.email,
        )
        task_id = async_task(
            "api.v1.v1_jobs.job.notify_verification_email",
            admin_user.email,
            admin_user.email_verification_code,
            hook="api.v1.v1_jobs.job.email_notification_results",
        )
        job.task_id = task_id
        job.save()
        # Create reviewer users
        for reviewer in reviewers_data:
            r = SystemUser.objects._create_user(
                name=reviewer['name'],
                email=reviewer['email'],
                password=SystemUser.objects.make_random_password(),
                role=UserRoleTypes.reviewer,
                organization_id=reviewer.get('organization_id')
            )
            job = Jobs.objects.create(
                type=JobTypes.verification_email,
                status=JobStatus.on_progress,
                result=reviewer["email"],
            )
            task_id = async_task(
                "api.v1.v1_jobs.job.notify_verification_email",
                reviewer["email"],
                r.email_verification_code,
                hook="api.v1.v1_jobs.job.email_notification_results",
            )
            job.task_id = task_id
            job.save()
        return admin_user

    class Meta:
        fields = [
            'name',
            'email',
            'password',
            'confirm_password',
            'reviewers'
        ]


class InitialUserResponseSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    reviewers = ReviewerSerializer(many=True, read_only=True)

    class Meta:
        fields = ['name', 'email', 'reviewers']

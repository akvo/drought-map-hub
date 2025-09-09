from datetime import datetime
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from api.v1.v1_rundeck.models import Settings
from utils.custom_serializer_fields import (
    CustomJSONField,
    CustomCharField,
    CustomIntegerField,
)


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = [
            "id",
            "project_name",
            "job_id",
            "job_config",
            "on_success_emails",
            "on_failure_emails",
            "on_exceeded_emails",
            "lst_weight",
            "ndvi_weight",
            "spi_weight",
            "sm_weight",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class UpdateSettingsSerializer(serializers.ModelSerializer):
    on_failure_emails = CustomJSONField(
        required=False,
        allow_null=True,
    )
    on_success_emails = CustomJSONField(
        required=False,
        allow_null=True,
    )
    on_exceeded_emails = CustomJSONField(
        required=False,
        allow_null=True,
    )
    job_config = CustomJSONField(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Settings
        fields = [
            "on_success_emails",
            "on_failure_emails",
            "on_exceeded_emails",
            "job_config",
            "lst_weight",
            "ndvi_weight",
            "spi_weight",
            "sm_weight",
        ]


class RundeckProjectSerializer(serializers.Serializer):
    name = CustomCharField()
    label = CustomCharField()

    class Meta:
        fields = ["name", "label"]


class RundeckJobSerializer(serializers.Serializer):
    id = CustomCharField()
    name = CustomCharField()
    permalink = CustomCharField()

    class Meta:
        fields = ["id", "name", "permalink"]


class RundeckExecutionJobSerializer(serializers.Serializer):
    id = CustomIntegerField()
    permalink = CustomCharField()
    status = CustomCharField()
    date_started = serializers.SerializerMethodField()
    date_ended = serializers.SerializerMethodField()
    year_month = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_date_started(self, instance):
        return instance["date-started"]["date"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_date_ended(self, instance):
        if instance.get("date-ended"):
            return instance["date-ended"]["date"]
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_year_month(self, instance):
        if instance["job"].get("options").get("year_month"):
            return instance["job"]["options"]["year_month"]
        return None

    class Meta:
        fields = [
            "id",
            "permalink",
            "status",
            "date_started",
            "date_ended",
            "year_month",
        ]


class ContactsSerializer(serializers.Serializer):
    contacts = CustomJSONField()

    class Meta:
        fields = ["contacts"]


class RundeckJobOptionsSerializer(serializers.Serializer):
    year_month = serializers.CharField()
    lst_weight = serializers.FloatField()
    ndvi_weight = serializers.FloatField()
    spi_weight = serializers.FloatField()
    sm_weight = serializers.FloatField()

    def validate_year_month(self, value):
        try:
            parsed_date = datetime.strptime(value, "%Y-%m")
            return parsed_date.strftime("%Y-%m")
        except ValueError:
            raise serializers.ValidationError(
                "Invalid date format. Use YYYY-MM."
            )

    class Meta:
        fields = [
            "year_month",
            "lst_weight",
            "ndvi_weight",
            "spi_weight",
            "sm_weight",
        ]

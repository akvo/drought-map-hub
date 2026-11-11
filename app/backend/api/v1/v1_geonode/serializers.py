from rest_framework import serializers

from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    PublicationStatus,
    RasterIndicatorTypes,
)
from utils.custom_serializer_fields import (
    CustomIntegerField,
    CustomCharField,
    CustomURLField,
    CustomDateTimeField,
    CustomChoiceField,
)


class PushGeonodePublicationSerializer(serializers.Serializer):
    geonode_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(
        choices=list(CDIGeonodeCategory.FieldStr.keys())
    )
    title = serializers.CharField(max_length=255)
    year_month = serializers.DateField()
    detail_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    embed_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    thumbnail_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    download_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    file_size = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )


class PushGeonodeRasterSerializer(serializers.Serializer):
    indicator = serializers.ChoiceField(
        choices=RasterIndicatorTypes.choices()
    )
    geonode_id = serializers.IntegerField(min_value=1)
    values = serializers.ListField(child=serializers.DictField())

    def validate_values(self, value):
        from django.core.exceptions import (
            ValidationError as DjangoValidationError,
        )
        from api.v1.v1_publication.models import validate_json_values

        try:
            validate_json_values(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class PushGeonodePublicationResponseSerializer(serializers.Serializer):
    geonode_id = serializers.IntegerField()
    synced_at = serializers.DateTimeField()


class PushGeonodeRasterResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    indicator = serializers.CharField()
    geonode_id = serializers.IntegerField()
    extracted_at = serializers.DateTimeField()


class CDIGeonodeFilterSerializer(serializers.Serializer):
    category = CustomChoiceField(
        choices=list(CDIGeonodeCategory.FieldStr.keys()),
        required=False,
        allow_null=True,
    )
    status = CustomChoiceField(
        choices=list(PublicationStatus.FieldStr.keys()),
        required=False,
        allow_null=False,
    )
    id = CustomIntegerField(
        required=False,
        allow_null=True,
    )

    class Meta:
        fields = ["category", "status", "id"]


class CDIGeonodeListSerializer(serializers.Serializer):
    pk = CustomIntegerField()
    title = CustomCharField()
    detail_url = CustomURLField()
    embed_url = CustomURLField()
    thumbnail_url = CustomURLField()
    download_url = CustomURLField()
    created = CustomDateTimeField()
    year_month = CustomCharField()
    publication_id = CustomIntegerField(
        allow_null=True
    )
    status = CustomIntegerField(
        allow_null=True
    )

    class Meta:
        fields = [
            "pk",
            "title",
            "detail_url",
            "embed_url",
            "thumbnail_url",
            "download_url",
            "created",
            "year_month",
            "publication_id",
            "status",
        ]

from rest_framework import serializers

from api.v1.v1_publication.constants import CDIGeonodeCategory


class PushGeonodePublicationSerializer(serializers.Serializer):
    """Payload the pipeline posts to attach GeoNode pointers to a raster.

    Carries the core metadata too (category/title/year_month) so the pointer
    sync can create the Raster if the core push has not run yet — the two
    pushes are order-independent.
    """

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


class PushGeonodePublicationResponseSerializer(serializers.Serializer):
    geonode_id = serializers.IntegerField()
    synced_at = serializers.DateTimeField()

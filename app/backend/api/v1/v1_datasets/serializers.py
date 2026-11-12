from rest_framework import serializers


class DatasetMetaSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    unit = serializers.CharField(allow_null=True)
    period = serializers.CharField(help_text="YYYY-MM")


class DatasetValueSerializer(serializers.Serializer):
    administration_id = serializers.IntegerField()
    value = serializers.FloatField(allow_null=True)


class DatasetResponseSerializer(serializers.Serializer):
    meta = DatasetMetaSerializer()
    data = DatasetValueSerializer(many=True)


class DatasetPeriodsSerializer(serializers.Serializer):
    key = serializers.CharField()
    periods = serializers.ListField(child=serializers.CharField())

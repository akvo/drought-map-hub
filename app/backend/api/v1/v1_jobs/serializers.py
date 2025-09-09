from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Jobs
from .constants import JobStatus, JobTypes
from utils.custom_serializer_fields import (
    CustomChoiceField,
    CustomCharField,
)


class JobSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    @extend_schema_field(
        CustomChoiceField(
            choices=[JobTypes.FieldStr[d] for d in JobTypes.FieldStr]
        )
    )
    def get_type(self, instance):
        return JobTypes.FieldStr.get(instance.type)

    @extend_schema_field(
        CustomChoiceField(
            choices=[JobStatus.FieldStr[d] for d in JobStatus.FieldStr]
        )
    )
    def get_status(self, instance):
        return JobStatus.FieldStr.get(instance.status)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    class Meta:
        model = Jobs
        fields = [
            "id",
            "task_id",
            "type",
            "status",
            "result",
            "created",
            "available"
        ]


class CreateJobSerializer(serializers.Serializer):
    name = CustomCharField()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    class Meta:
        fields = ["name"]


class FeedbackSerializer(serializers.Serializer):
    email = CustomCharField()
    feedback = CustomCharField()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    class Meta:
        fields = ["email", "feedback"]

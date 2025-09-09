from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from collections import defaultdict
from .models import (
    Administration,
    Publication,
    Review,
)
from utils.custom_serializer_fields import (
    CustomIntegerField,
    CustomCharField,
    CustomURLField,
    CustomDateTimeField,
    CustomListField,
    CustomPrimaryKeyRelatedField,
    CustomChoiceField,
    CustomJSONField,
    CustomDateField,
)
from api.v1.v1_users.serializers import UserReviewerSerializer
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.constants import (
    DroughtCategory,
    ExportMapTypes,
    CDIGeonodeCategory,
    PublicationStatus,
)


class AdministrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administration
        fields = [
            "id",
            "name",
            "region",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PublicationSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(format="%Y-%m")
    progress_reviews = serializers.SerializerMethodField()
    reviewers = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_reviews(self, obj):
        total_reviews = obj.reviews.count()
        total_completed = obj.reviews.filter(is_completed=True).count()
        return f"{total_completed}/{total_reviews}"

    @extend_schema_field(OpenApiTypes.ANY)
    def get_reviewers(self, obj):
        reviewers = [
            {
                "review_id": review.id,
                "is_completed": review.is_completed,
                **UserReviewerSerializer(instance=review.user).data,
            }
            for review in obj.reviews.all()
        ]
        return reviewers

    class Meta:
        model = Publication
        fields = [
            "id",
            "cdi_geonode_id",
            "year_month",
            "initial_values",
            "status",
            "due_date",
            "validated_values",
            "published_at",
            "narrative",
            "bulletin_url",
            "created_at",
            "updated_at",
            "progress_reviews",
            "reviewers",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "progress_reviews",
            "reviewers",
        ]

    def __init__(self, *args, **kwargs):
        super(PublicationSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'PUT':
            for field in self.fields:
                self.fields[field].required = False


class PublicationInfoSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(format="%Y-%m")

    class Meta:
        model = Publication
        fields = [
            "id",
            "year_month",
            "due_date",
            "initial_values",
            "status",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    publication = PublicationInfoSerializer(read_only=True)
    progress_review = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_review(self, obj):
        suggestion_values = obj.suggestion_values or []
        reviewed_count = sum(
            1 for item in suggestion_values if item.get("reviewed") is True
        )
        total = len(obj.publication.initial_values)
        return f"{reviewed_count}/{total}"

    # Add suggestion_values validation on create and update
    # to ensure category is not None when reviewed is True
    def validate_suggestion_values(self, value):
        if not value:
            return value
        for i, suggestion in enumerate(value):
            # Only validate category is not None when reviewed is True
            reviewed = suggestion.get("reviewed", False)
            category = suggestion.get("category")
            # Check if category is invalid when reviewed is True
            if reviewed:
                if category is None or (category != 0 and not category):
                    admin_id = suggestion.get('administration_id')
                    raise serializers.ValidationError(
                        f"Category required when reviewed is True "
                        f"(item #{i+1}, administration_id: {admin_id})"
                    )
        return value

    class Meta:
        model = Review
        fields = [
            "id",
            "publication_id",
            "publication",
            "user_id",
            "is_completed",
            "suggestion_values",
            "created_at",
            "updated_at",
            "completed_at",
            "progress_review",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ReviewListSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(
        source="publication.year_month",
        format="%Y-%m"
    )
    due_date = serializers.DateField(
        source="publication.due_date",
        format="%Y-%m-%d"
    )
    progress_review = serializers.SerializerMethodField()
    publication_id = serializers.IntegerField(source="publication.id")

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_review(self, obj):
        # Filter for suggestion values where reviewed is True
        suggestion_values = obj.suggestion_values or []
        reviewed_count = sum(
            1 for item in suggestion_values if item.get('reviewed') is True
        )
        # total = len(list(filter(
        #     lambda x: x["category"] != DroughtCategory.none,
        #     obj.publication.initial_values
        # )))
        total = len(obj.publication.initial_values)
        return f"{reviewed_count}/{total}"

    class Meta:
        model = Review
        fields = [
            "id",
            "publication_id",
            "year_month",
            "due_date",
            "completed_at",
            "is_completed",
            "progress_review",
        ]


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


class PublicationReviewsSerializer(serializers.ModelSerializer):
    reviews = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.ANY)
    def get_reviews(self, obj):
        non_disputed = self.context.get("non_disputed", False)
        non_validated = self.context.get("non_validated", False)
        validated_values = obj.validated_values or []
        no_data_ids = [
            v["administration_id"]
            # for v in list(filter(
            #     lambda x: x["category"] == DroughtCategory.none,
            #     obj.initial_values
            # ))
            for v in obj.initial_values
        ]
        non_validated_ids = [
            v["administration_id"]
            for v in list(filter(
                lambda x: (
                    x.get("category") is None
                    or x["administration_id"] not in no_data_ids
                ),
                validated_values
            ))
        ]

        reviews = [
            {
                **s,
                "user_id": review.user.id,
            }
            for review in obj.completed_reviews
            for s in review.suggestion_values
        ]

        if non_disputed:
            filtered_reviews = []
            grouped_reviews = defaultdict(list)
            reviews = reviews + obj.initial_values
            for review in reviews:
                if review["category"] != DroughtCategory.none:
                    grouped_reviews[review["administration_id"]].append(review)
            for _, admin_reviews in grouped_reviews.items():
                categories = {r["category"] for r in admin_reviews}
                if len(categories) == 1:
                    filtered_reviews.extend(admin_reviews)
            reviews = filtered_reviews

        if non_validated and (
            len(non_validated_ids) or
            len(non_validated_ids) == 0 and len(obj.validated_values)
        ):
            reviews = [
                r for r in reviews
                if r["administration_id"] in non_validated_ids
            ]

        return reviews

    @extend_schema_field(OpenApiTypes.ANY)
    def get_users(self, obj):
        return UserReviewerSerializer(
            instance=[
                r.user
                for r in obj.completed_reviews
            ],
            many=True
        ).data

    class Meta:
        model = Publication
        fields = [
            "id",
            "validated_values",
            "reviews",
            "users",
        ]


class CreatePublicationSerializer(serializers.ModelSerializer):
    initial_values = CustomJSONField()
    year_month = CustomDateField()
    due_date = CustomDateField()
    reviewers = CustomListField(
        child=CustomPrimaryKeyRelatedField(
            queryset=SystemUser.objects.none()
        ),
        required=True,
    )
    subject = CustomCharField()
    message = CustomCharField()
    download_url = CustomCharField()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields.get("reviewers").child.queryset = SystemUser.objects \
            .filter(
                role=UserRoleTypes.reviewer
            ).all()

    def validate_due_date(self, value):
        today = timezone.now().date()
        if value < today:
            raise serializers.ValidationError(
                "The date must be today or later."
            )
        return value

    def validate_reviewers(self, value):
        if len(value) == 0:
            raise serializers.ValidationError(
                "Please select at least one reviewer."
            )
        return value

    def to_representation(self, instance):
        return PublicationSerializer(instance).data

    class Meta:
        model = Publication
        fields = [
            "cdi_geonode_id",
            "year_month",
            "initial_values",
            "due_date",
            "reviewers",
            "subject",
            "message",
            "download_url",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ReviewInfoSerializer(serializers.ModelSerializer):
    publication = PublicationInfoSerializer(read_only=True)
    user = UserReviewerSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "publication",
            "user",
            "suggestion_values",
            "created_at",
            "updated_at",
            "completed_at",
        ]


class ExportMapSerializer(serializers.Serializer):
    export_type = CustomChoiceField(
        choices=list(ExportMapTypes.FieldStr.keys()),
        required=False,
        allow_null=True,
    )

    class Meta:
        fields = [
            "export_type"
        ]


class PublishedMapSerializer(serializers.ModelSerializer):

    class Meta:
        model = Publication
        fields = [
            "id",
            "cdi_geonode_id",
            "year_month",
            "validated_values",
            "published_at",
            "narrative",
            "bulletin_url",
            "created_at",
            "updated_at",
        ]


class CompareMapSerializer(serializers.Serializer):
    left_date = CustomDateField(required=False)
    right_date = CustomDateField(required=False)

    class Meta:
        fields = [
            "left_date",
            "right_date"
        ]

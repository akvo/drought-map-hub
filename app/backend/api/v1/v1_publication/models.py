from django.db import models
from django.core.exceptions import ValidationError
from utils.soft_deletes_model import SoftDeletes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.constants import PublicationStatus


class Administration(models.Model):
    name = models.CharField(max_length=100, null=False)
    region = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "administrations"


def validate_json_values(json_values: list = []):
    if not isinstance(json_values, list):
        raise ValidationError(
            "JSON values must be a list of objects."
        )
    for item in json_values:  # pragma: no cover
        if not isinstance(item, dict):
            raise ValidationError(
                "Each item in JSON must be a dictionary."
            )
        if "administration_id" not in item:
            raise ValidationError(
                "Each item must contain an 'administration_id' key."
            )
        # if "value" not in item:
        #     raise ValidationError(
        #         "Each item must contain a 'value' key."
        #     )


class Publication(SoftDeletes):
    year_month = models.DateField(null=False)
    cdi_geonode_id = models.IntegerField(null=False, unique=True)
    initial_values = models.JSONField(
        null=False,
        validators=[validate_json_values]
    )
    validated_values = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_json_values]
    )
    due_date = models.DateField(null=False)
    status = models.IntegerField(
        choices=PublicationStatus.FieldStr.items(),
        default=PublicationStatus.in_review,
        null=True
    )
    narrative = models.TextField(null=True, blank=True)
    bulletin_url = models.URLField(max_length=255, null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"Publication: {self.cdi_geonode_id} - "
            f"{self.year_month.strftime('%Y-%m')}"
        )

    @property
    def completed_reviews(self):
        return self.reviews.filter(
            is_completed=True,
            completed_at__isnull=False,
        )

    class Meta:
        db_table = "publications"


class Review(models.Model):
    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    user = models.ForeignKey(
        SystemUser,
        on_delete=models.CASCADE
    )
    is_completed = models.BooleanField(default=False)
    suggestion_values = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_json_values]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_overdue_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"Review: {self.publication.year_month} by {self.user.email}"

    class Meta:
        db_table = "reviews"

from django.db import models
from django.core.exceptions import ValidationError
from utils.soft_deletes_model import SoftDeletes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.constants import PublicationStatus


class Administration(models.Model):
    name = models.CharField(max_length=100, null=False)
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
    # The source raster asset this publication was created from. This is the
    # real relation (not keyed on any GeoNode id): one Raster -> at most one
    # Publication. raster.publication gives the reverse. Nullable so a fully
    # manual publication can exist without an asset.
    raster = models.OneToOneField(
        "Raster",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="publication",
    )
    # Legacy loose reference to a GeoNode resource id. Kept during the
    # Raster-asset migration (frontend/create-flow still pass it); the GeoNode
    # ref now lives on Raster.geonode_id. Not used for the Publication relation.
    # unique still holds for non-null ids (Postgres treats NULLs as distinct).
    cdi_geonode_id = models.IntegerField(null=True, blank=True, unique=True)
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


class Raster(models.Model):
    """A raster map output stored on the platform as a publication asset.

    Holds the per-administration ``values`` reduced from the source raster, so
    the publication workflow (listing, create, review) never has to reach an
    external raster store. ``geonode_id`` is an optional reference to the
    GeoNode resource that hosts the full raster; the optional ``v1_geonode``
    module attaches live GeoNode pointers (detail/embed/download URLs) to this
    asset via a FK. With no raster store at all the asset still stands on its
    pushed ``values`` alone.
    """

    geonode_id = models.IntegerField(null=True, blank=True, unique=True)
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    # normalised to first-of-month by save() (readers look up by <YYYY-MM>-01)
    year_month = models.DateField()
    # per-administration reduced values, pushed by the pipeline
    values = models.JSONField(
        null=True, blank=True, validators=[validate_json_values]
    )
    # source raster `created` datetime (for display/sort)
    resource_created = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # auto-updated on every push/sync write
    synced_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        year_month = self._meta.get_field("year_month").to_python(
            self.year_month
        )
        if year_month and year_month.day != 1:
            self.year_month = year_month.replace(day=1)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Raster:{self.geonode_id} ({self.year_month})"

    class Meta:
        db_table = "rasters"
        indexes = [models.Index(fields=["category", "year_month"])]

from django.db import models

from api.v1.v1_publication.models import Publication, validate_json_values
from api.v1.v1_publication.constants import RasterIndicatorTypes


class PublicationRaster(models.Model):
    """Pre-computed per-indicator raster values for a publication.

    This is the **GeoNode-down resilience** fallback (DIH-1): when GeoNode is
    unreachable while the ``geonode`` module is still ON, the pipeline pushes
    these values so the review workflow does not need to fetch the raster. It
    is NOT a geonode-OFF mode: both this model and its push endpoint live under
    the ``geonode`` module gate, so they are intentionally absent when the
    module is disabled. A hub that must run without GeoNode at all is a separate
    design (see DIH-1 open questions) and is not covered here.
    """

    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, related_name="rasters"
    )
    indicator = models.CharField(
        max_length=10, choices=RasterIndicatorTypes.choices()
    )
    geonode_id = models.IntegerField()
    values = models.JSONField(
        null=True, blank=True, validators=[validate_json_values]
    )
    extracted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.publication_id}:{self.indicator}"

    class Meta:
        db_table = "publication_rasters"
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "indicator"],
                name="uniq_publication_raster_indicator",
            )
        ]


class PublicationGeonode(models.Model):
    """Cached GeoNode resource metadata — the geodata the publication
    list/detail needs, so reads survive GeoNode downtime (D-1/D-2).

    One row per GeoNode raster resource. Refreshed by two writers only:
      - the CDI pipeline push (POST /geonode/publications, steady state)
      - the sync_publication_geonodes backfill command (history / recovery)
    The read path (CDIGeonodeAPI.get) never calls GeoNode at all.
    """

    geonode_id = models.IntegerField(unique=True)
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    # resource `date`, normalised to first-of-month by save()
    year_month = models.DateField()
    subtype = models.CharField(max_length=20, default="raster")
    detail_url = models.URLField(max_length=512, null=True, blank=True)
    embed_url = models.URLField(max_length=512, null=True, blank=True)
    thumbnail_url = models.URLField(max_length=512, null=True, blank=True)
    download_url = models.URLField(max_length=512, null=True, blank=True)
    # bytes; frontend formats as e.g. "200 KB"
    file_size = models.BigIntegerField(null=True, blank=True)
    # GeoNode resource `created` datetime
    resource_created = models.DateTimeField(null=True, blank=True)
    # full GeoNode payload kept for forward-compatibility
    raw = models.JSONField(null=True, blank=True)
    # auto-updated on every cache write
    synced_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Every reader looks this row up by month and asks for
        # year_month=<YYYY-MM>-01. GeoNode's resource `date` is a full date,
        # so a resource dated the 31st would never be found. Normalise on the
        # way in so all writers (pipeline push, backfill, seeder) agree.
        # to_python handles a date or an ISO string interchangeably.
        year_month = self._meta.get_field("year_month").to_python(
            self.year_month
        )
        if year_month and year_month.day != 1:
            self.year_month = year_month.replace(day=1)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"PublicationGeonode:{self.geonode_id} ({self.year_month})"

    class Meta:
        db_table = "publication_geonodes"
        indexes = [models.Index(fields=["category", "year_month"])]

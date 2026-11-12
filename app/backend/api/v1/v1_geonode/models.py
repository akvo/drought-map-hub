from django.db import models


class GeoNodeResource(models.Model):
    """GeoNode location pointers for a platform Raster asset (DIH-1).

    The optional ``geonode`` module's whole footprint: a thin pointer row that
    enriches a core ``Raster`` with the URLs of the GeoNode resource hosting
    it (detail / embed / thumbnail / download). The raster's metadata and
    per-administration values live on the core ``Raster`` itself, so with this
    module off the asset still stands — only these deep links are absent.

    One GeoNode resource per raster (OneToOne); deleting the raster removes the
    pointer.
    """

    raster = models.OneToOneField(
        "v1_publication.Raster",
        on_delete=models.CASCADE,
        related_name="geonode_resource",
    )
    detail_url = models.URLField(max_length=512, null=True, blank=True)
    embed_url = models.URLField(max_length=512, null=True, blank=True)
    thumbnail_url = models.URLField(max_length=512, null=True, blank=True)
    download_url = models.URLField(max_length=512, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    raw = models.JSONField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"GeoNodeResource:{self.raster_id}"

    class Meta:
        db_table = "geonode_resources"

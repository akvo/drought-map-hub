from django.db import models


def default_modules():
    # DIH-9: per-client optional-module flags. GeoNode on by default so an
    # unconfigured instance keeps today's behaviour.
    return {"geonode": True, "weather": False, "iks": False}


class SiteConfig(models.Model):
    uuid = models.CharField(max_length=36, unique=True)
    name = models.CharField(max_length=155)
    country = models.CharField(max_length=155, blank=True, null=True)
    geojson_file = models.CharField(max_length=191, blank=True, null=True)
    map_center = models.JSONField(blank=True, null=True)
    map_name_key = models.CharField(max_length=55, blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#3E5EB9")
    modules = models.JSONField(default=default_modules)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "site_config"


class Organization(models.Model):
    name = models.CharField(max_length=255)
    website = models.URLField(max_length=200, blank=True, null=True)
    logo = models.ImageField(
        upload_to='organization_logos/', blank=True, null=True
    )
    is_twg = models.BooleanField(default=False)
    is_collaborator = models.BooleanField(default=False)
    is_host = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "organizations"

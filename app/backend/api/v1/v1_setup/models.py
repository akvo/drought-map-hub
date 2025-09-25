from django.db import models


class SiteConfig(models.Model):
    uuid = models.CharField(max_length=36, unique=True)
    name = models.CharField(max_length=155)
    country = models.CharField(max_length=155, blank=True, null=True)
    geojson_file = models.CharField(max_length=191, blank=True, null=True)
    map_center = models.JSONField(blank=True, null=True)
    map_name_key = models.CharField(max_length=55, blank=True, null=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "organizations"

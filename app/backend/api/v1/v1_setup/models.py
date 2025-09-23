from django.db import models


class SiteConfig(models.Model):
    uuid = models.CharField(max_length=36, unique=True)
    name = models.CharField(max_length=255)
    geojson_file = models.CharField(max_length=255, blank=True, null=True)
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

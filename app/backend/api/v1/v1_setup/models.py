from django.db import models

from utils.modules import module_enabled

# Optional modules the setup wizard (DIH-9) exposes.
WIZARD_MODULES = ("geonode", "weather", "iks")


def default_modules():
    # DIH-2/DIH-9: a fresh instance mirrors the deployment's DIH_MODULES env
    # (via module_enabled) so the wizard/frontend flags agree with the backend
    # route gate instead of a hardcoded default. DIH_MODULES unset -> all on.
    return {name: module_enabled(name) for name in WIZARD_MODULES}


class SiteConfig(models.Model):
    uuid = models.CharField(max_length=36, unique=True)
    name = models.CharField(max_length=155)
    country = models.CharField(max_length=155, blank=True, null=True)
    geojson_file = models.CharField(max_length=191, blank=True, null=True)
    map_center = models.JSONField(blank=True, null=True)
    map_name_key = models.CharField(max_length=55, blank=True, null=True)
    theme = models.CharField(max_length=50, default="Ocean Blue")
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

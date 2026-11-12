from importlib import import_module, reload

from django.conf import settings
from django.test.utils import override_settings
from django.urls import clear_url_caches
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.models import Raster
from api.v1.v1_geonode.models import GeoNodeResource


def reload_urlconf():
    """Re-evaluate the root URLconf so a changed DIH_MODULES takes effect
    (the geonode include is conditional at import time)."""
    clear_url_caches()
    reload(import_module(settings.ROOT_URLCONF))


# Default test settings leave DIH_MODULES unset -> geonode on, so these
# "module on" cases need no urlconf reload.
@override_settings(X_API_KEY="test-key")
class GeonodePushAPITest(APITestCase):
    def setUp(self):
        self.url = "/api/v1/geonode/publications"
        self.payload = {
            "geonode_id": 101,
            "category": "cdi-raster-map",
            "title": "CDI 2025-07",
            "year_month": "2025-07-15",
            "detail_url": "https://geonode.example/catalogue/#/dataset/101",
            "download_url": "https://geonode.example/datasets/101/download",
            "file_size": 2048,
        }

    def test_push_requires_api_key(self):
        res = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_push_creates_raster_and_pointer(self):
        res = self.client.post(
            self.url, self.payload, format="json", HTTP_X_API_KEY="test-key"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        raster = Raster.objects.get(geonode_id=101)
        # the core raster is created with its metadata (month normalised)
        self.assertEqual(str(raster.year_month), "2025-07-01")
        resource = GeoNodeResource.objects.get(raster=raster)
        self.assertEqual(resource.file_size, 2048)
        self.assertEqual(
            resource.download_url,
            "https://geonode.example/datasets/101/download",
        )

    def test_push_upserts_same_pointer(self):
        self.client.post(
            self.url, self.payload, format="json", HTTP_X_API_KEY="test-key"
        )
        res2 = self.client.post(
            self.url,
            {**self.payload, "detail_url": "https://geonode.example/new"},
            format="json", HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(Raster.objects.count(), 1)
        self.assertEqual(GeoNodeResource.objects.count(), 1)
        resource = GeoNodeResource.objects.get(raster__geonode_id=101)
        self.assertEqual(resource.detail_url, "https://geonode.example/new")

    def test_push_reuses_existing_raster(self):
        # core push (POST /api/v1/rasters) already created the raster
        raster = Raster.objects.create(
            geonode_id=101, category="cdi-raster-map",
            title="CDI 2025-07", year_month="2025-07-01",
            values=[{"administration_id": 1, "value": 2, "category": 2}],
        )
        self.client.post(
            self.url, self.payload, format="json", HTTP_X_API_KEY="test-key"
        )
        self.assertEqual(Raster.objects.count(), 1)
        raster.refresh_from_db()
        # pointer push must not clobber the already-pushed values
        self.assertEqual(len(raster.values), 1)
        self.assertTrue(
            GeoNodeResource.objects.filter(raster=raster).exists()
        )


class GeonodeModuleOffTest(APITestCase):
    def test_push_404_when_module_disabled(self):
        with override_settings(DIH_MODULES=[]):
            reload_urlconf()
            try:
                res = self.client.post(
                    "/api/v1/geonode/publications", {}, format="json"
                )
                self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
            finally:
                pass
        reload_urlconf()

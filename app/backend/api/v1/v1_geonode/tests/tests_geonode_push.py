from importlib import import_module, reload

from django.conf import settings
from django.test.utils import override_settings
from django.urls import clear_url_caches
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_geonode.models import PublicationGeonode


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
        self.pub_url = "/api/v1/geonode/publications"
        self.payload = {
            "geonode_id": 101,
            "category": "cdi-raster-map",
            "title": "CDI 2025-07",
            "year_month": "2025-07-15",
        }

    def test_push_requires_api_key(self):
        res = self.client.post(self.pub_url, self.payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_push_upserts_and_normalises_month(self):
        res = self.client.post(
            self.pub_url, self.payload, format="json",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        obj = PublicationGeonode.objects.get(geonode_id=101)
        # save() normalises resource date to first-of-month
        self.assertEqual(str(obj.year_month), "2025-07-01")
        # second push updates the same row, not a duplicate
        res2 = self.client.post(
            self.pub_url, {**self.payload, "title": "CDI updated"},
            format="json", HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(PublicationGeonode.objects.count(), 1)
        obj.refresh_from_db()
        self.assertEqual(obj.title, "CDI updated")

    def test_raster_push_requires_api_key(self):
        res = self.client.post(
            "/api/v1/geonode/publications/999/rasters", {}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_raster_push_missing_publication_404(self):
        res = self.client.post(
            "/api/v1/geonode/publications/999/rasters",
            {"indicator": "spi", "geonode_id": 5, "values": []},
            format="json", HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class GeonodeModuleOffTest(APITestCase):
    def test_endpoints_404_when_module_disabled(self):
        with override_settings(DIH_MODULES=[]):
            reload_urlconf()
            try:
                pub = self.client.post(
                    "/api/v1/geonode/publications", {}, format="json"
                )
                ras = self.client.post(
                    "/api/v1/geonode/publications/1/rasters", {},
                    format="json",
                )
                self.assertEqual(pub.status_code, status.HTTP_404_NOT_FOUND)
                self.assertEqual(ras.status_code, status.HTTP_404_NOT_FOUND)
            finally:
                # settings revert on exit; rebuild urlconf with geonode on
                pass
        reload_urlconf()

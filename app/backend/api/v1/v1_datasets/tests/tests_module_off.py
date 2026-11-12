from importlib import import_module, reload

from django.conf import settings
from django.test.utils import override_settings
from django.urls import clear_url_caches
from rest_framework import status
from rest_framework.test import APITestCase


def reload_urlconf():
    """Re-evaluate the root URLconf so a changed DIH_MODULES takes effect
    (the datasets include is conditional at import time)."""
    clear_url_caches()
    reload(import_module(settings.ROOT_URLCONF))


class DatasetsModuleOffTest(APITestCase):
    def test_routes_404_when_module_disabled(self):
        with override_settings(DIH_MODULES=[]):
            reload_urlconf()
            try:
                for url in (
                    "/api/v1/datasets/ndvi_anomaly",
                    "/api/v1/datasets/ndvi_anomaly/periods",
                ):
                    res = self.client.get(url)
                    self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
            finally:
                reload_urlconf()

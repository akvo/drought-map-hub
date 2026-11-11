from datetime import datetime, timezone as dt_timezone
from importlib import import_module, reload

from django.conf import settings
from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import clear_url_caches
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.models import Publication, PublicationStatus
from api.v1.v1_publication.constants import DroughtCategory, CDIGeonodeCategory
from api.v1.v1_geonode.models import PublicationGeonode


def reload_urlconf():
    clear_url_caches()
    reload(import_module(settings.ROOT_URLCONF))


class CDIGeonodeReadAPITestCase(APITestCase):
    """The read path serves the PublicationGeonode cache, never GeoNode."""

    def setUp(self):
        self.url = "/api/v1/admin/cdi-geonode"
        call_command("generate_admin_seeder", "--test", True)
        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).order_by("?").first()
        self.client.force_authenticate(user=self.user)

        created = datetime(2025, 1, 15, 12, 0, tzinfo=dt_timezone.utc)
        PublicationGeonode.objects.create(
            geonode_id=1,
            category=CDIGeonodeCategory.cdi,
            title="Test GeoNode Resource",
            year_month="2024-12-31",
            detail_url="https://geonode.com/catalogue/#/dataset/1",
            embed_url="https://geonode.com/datasets/geonode:test/embed",
            thumbnail_url="https://geonode.com/thumbs/a.jpg",
            download_url="https://geonode.com/datasets/geonode:test/download",
            resource_created=created,
        )
        PublicationGeonode.objects.create(
            geonode_id=2,
            category=CDIGeonodeCategory.cdi,
            title="Another Resource",
            year_month="2024-11-20",
            detail_url="https://geonode.com/catalogue/#/dataset/2",
            embed_url="https://geonode.com/datasets/geonode:another/embed",
            thumbnail_url="https://geonode.com/thumbs/b.jpg",
            download_url="https://geonode.com/datasets/geonode:another/dl",
            resource_created=created,
        )

    def test_list_from_cache(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        # ordered by year_month desc -> December first
        self.assertEqual(response.data["data"][0]["pk"], 1)
        self.assertEqual(
            response.data["data"][0]["title"], "Test GeoNode Resource"
        )

    def test_publication_merge(self):
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2024-12-01",
            due_date="2025-01-31",
            initial_values=[{
                "administration_id": 1,
                "value": 6,
                "category": DroughtCategory.d3,
            }],
        )
        response = self.client.get(
            f"{self.url}?status={PublicationStatus.in_review}"
            f"&category={CDIGeonodeCategory.cdi}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"][0]["publication_id"], publication.pk
        )
        self.assertEqual(
            response.data["data"][0]["status"], PublicationStatus.in_review
        )

    def test_status_filter_no_match_is_empty(self):
        response = self.client.get(
            f"{self.url}?status={PublicationStatus.in_validation}"
            f"&category={CDIGeonodeCategory.cdi}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 0)

    def test_detail_by_id(self):
        response = self.client.get(f"{self.url}?id=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(response.data),
            [
                "pk", "title", "detail_url", "embed_url", "thumbnail_url",
                "download_url", "created", "year_month", "publication_id",
                "status",
            ],
        )

    def test_detail_missing_is_500(self):
        response = self.client.get(f"{self.url}?id=9999")
        self.assertEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def test_invalid_category_is_400(self):
        response = self.client.get(f"{self.url}?category=invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_is_401(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED
        )


class CDIGeonodeReadModuleOffTest(APITestCase):
    def test_read_route_404_when_module_disabled(self):
        with override_settings(DIH_MODULES=[]):
            reload_urlconf()
            try:
                res = self.client.get("/api/v1/admin/cdi-geonode")
                self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
            finally:
                pass
        reload_urlconf()

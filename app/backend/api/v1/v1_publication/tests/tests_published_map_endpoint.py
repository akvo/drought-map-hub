from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from api.v1.v1_publication.models import (
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory


@override_settings(USE_TZ=False, TEST_ENV=True)
class PublishedMapViewSetTestCase(APITestCase):
    def setUp(self):
        self.published = Publication.objects.create(
            year_month="2025-02-01",
            cdi_geonode_id=44,
            due_date="2025-03-29",
            initial_values=[
                {"administration_id": 11, "category": DroughtCategory.d2},
                {"administration_id": 12, "category": DroughtCategory.d4},
                {"administration_id": 13, "category": DroughtCategory.normal},
            ],
            validated_values=[
                {"administration_id": 11, "category": DroughtCategory.d2},
                {"administration_id": 12, "category": DroughtCategory.d1},
                {"administration_id": 13, "category": DroughtCategory.normal},
            ],
            status=PublicationStatus.published,
            narrative="Lorem ipsum dolor amet...",
            published_at=timezone.now(),
        )

    def test_get_published_map_list(self):
        url = reverse("maps", kwargs={"version": "v1"})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(response.data),
            [
                "current",
                "total",
                "total_page",
                "data",
            ],
        )
        self.assertEqual(
            list(response.data["data"][0]),
            [
                "id",
                "cdi_geonode_id",
                "year_month",
                "validated_values",
                "published_at",
                "narrative",
                "bulletin_url",
                "created_at",
                "updated_at",
            ],
        )

    def test_get_published_map_details(self):
        url = reverse(
            "map-details",
            kwargs={"version": "v1", "pk": self.published.id}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(response.data),
            [
                "id",
                "cdi_geonode_id",
                "year_month",
                "validated_values",
                "published_at",
                "narrative",
                "bulletin_url",
                "created_at",
                "updated_at",
            ],
        )
        self.assertIsNotNone(response.data["id"])
        self.assertIsNone(response.data["bulletin_url"])

    def test_filter_published_map_by_left_right_date(self):
        Publication.objects.create(
            year_month="2025-03-01",
            cdi_geonode_id=106,
            due_date="2025-04-30",
            initial_values=[
                {"administration_id": 11, "category": DroughtCategory.d1},
                {"administration_id": 12, "category": DroughtCategory.d0},
                {"administration_id": 13, "category": DroughtCategory.normal},
            ],
            validated_values=[
                {"administration_id": 11, "category": DroughtCategory.d2},
                {"administration_id": 12, "category": DroughtCategory.d1},
                {"administration_id": 13, "category": DroughtCategory.d4},
            ],
            status=PublicationStatus.published,
            narrative="Lorem ipsum dolor amet...",
            published_at=timezone.now(),
        )

        url = reverse("maps", kwargs={"version": "v1"})
        response = self.client.get(
            f"{url}?left_date=2025-02-01&right_date=2025-03-01",
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["total"],
            2
        )

    def test_get_published_map_details_404(self):
        url = reverse(
            "map-details",
            kwargs={"version": "v1", "pk": 9999}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

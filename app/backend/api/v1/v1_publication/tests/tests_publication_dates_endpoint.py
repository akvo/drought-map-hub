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
        self.repeat = 3
        publications = []
        for x in range(self.repeat):
            p = Publication.objects.create(
                year_month=f"2025-0{x + 2}-01",
                cdi_geonode_id=44 + x,
                due_date=f"2025-0{x + 3}-01",
                initial_values=[
                    {"administration_id": 11, "category": DroughtCategory.d2},
                    {"administration_id": 12, "category": DroughtCategory.d4},
                    {
                        "administration_id": 13,
                        "category": DroughtCategory.normal
                    },
                ],
                validated_values=[
                    {"administration_id": 11, "category": DroughtCategory.d2},
                    {"administration_id": 12, "category": DroughtCategory.d1},
                    {
                        "administration_id": 13,
                        "category": DroughtCategory.normal
                    },
                ],
                status=PublicationStatus.published,
                narrative="Lorem ipsum dolor amet...",
                published_at=timezone.now(),
            )
            publications.append(p)
        self.publications = publications

    def test_success_get_all_dates(self):
        response = self.client.get(
            reverse("publication-dates", kwargs={"version": "v1"})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(response.data[0]), ["value", "label"])
        self.assertEqual(len(response.data), self.repeat)

    def test_success_get_dates_by_excluding_id(self):
        url = reverse("publication-dates", kwargs={"version": "v1"})
        selected = Publication.objects.order_by("?").first()
        response = self.client.get(f"{url}?exclude_id={selected.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(selected.id not in [r["value"] for r in response.data])

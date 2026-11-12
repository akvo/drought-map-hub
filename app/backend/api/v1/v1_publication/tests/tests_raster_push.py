from unittest.mock import patch

from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.models import Publication, Raster
from api.v1.v1_jobs.models import Jobs, JobTypes


@override_settings(X_API_KEY="test-key")
class RasterPushAPITest(APITestCase):
    def setUp(self):
        self.url = "/api/v1/rasters"
        self.payload = {
            "geonode_id": 101,
            "category": "cdi-raster-map",
            "title": "CDI 2025-07",
            "year_month": "2025-07-15",
        }

    def test_push_requires_api_key(self):
        res = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_push_upserts_and_normalises_month(self):
        res = self.client.post(
            self.url, self.payload, format="json", HTTP_X_API_KEY="test-key"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        raster = Raster.objects.get(geonode_id=101)
        self.assertEqual(str(raster.year_month), "2025-07-01")

        # second push updates the same row, not a duplicate
        res2 = self.client.post(
            self.url, {**self.payload, "title": "CDI updated"},
            format="json", HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(Raster.objects.count(), 1)
        raster.refresh_from_db()
        self.assertEqual(raster.title, "CDI updated")

    def test_metadata_repush_keeps_existing_values(self):
        values = [{"administration_id": 1, "value": 2.5, "category": 3}]
        self.client.post(
            self.url, {**self.payload, "values": values},
            format="json", HTTP_X_API_KEY="test-key",
        )
        # metadata-only re-push (no values) must not wipe them
        self.client.post(
            self.url, {**self.payload, "title": "meta only"},
            format="json", HTTP_X_API_KEY="test-key",
        )
        raster = Raster.objects.get(geonode_id=101)
        self.assertEqual(raster.values, values)


@override_settings(USE_TZ=False, TEST_ENV=True)
class CreateFromRasterValuesTest(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 3)
        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.client.force_authenticate(user=self.user)
        self.reviewers = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        )[:2]

    @patch("django.utils.timezone.now")
    def test_create_uses_pushed_values_and_skips_download(
        self, mock_now
    ):
        mock_now.return_value = timezone.datetime(2025, 1, 31)
        values = [
            {"value": 3.5, "administration_id": 1253002, "category": 4},
        ]
        raster = Raster.objects.create(
            geonode_id=7, category="cdi-raster-map",
            title="CDI 2025-01", year_month="2025-01-01", values=values,
        )
        url = reverse("publication-list", kwargs={"version": "v1"})
        res = self.client.post(url, {
            "cdi_geonode_id": 7,
            "year_month": "2025-01-01",
            # deliberately different from the pushed values: the asset wins
            "initial_values": [
                {"value": 0, "administration_id": 1253002, "category": 0},
            ],
            "due_date": "2025-02-28",
            "reviewers": [r.id for r in self.reviewers],
            "subject": "review",
            "message": "{{reviewer_name}} {{year_month}} {{due_date}}",
            "download_url": "https://geonode.example/d/dataset_download",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        pub = Publication.objects.get(pk=res.json()["id"])
        # values came from the raster asset, not the request / a download
        self.assertEqual(pub.initial_values, values)
        self.assertEqual(pub.raster_id, raster.pk)
        # the GeoNode raster-download job was skipped entirely (notification
        # jobs may still be enqueued by notify_reviewers)
        self.assertEqual(
            Jobs.objects.filter(
                type=JobTypes.download_geonode_dataset
            ).count(),
            0,
        )

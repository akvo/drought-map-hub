from unittest.mock import patch

from django.core.management import call_command
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import CDIGeonodeCategory
from api.v1.v1_geonode.models import PublicationGeonode


def _mock_page(resources, total):
    mock = patch("requests.get").start()
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = {
        "resources": resources, "total": total
    }
    return mock


class SyncPublicationGeonodesTest(APITestCase):
    def tearDown(self):
        patch.stopall()

    def test_backfill_upserts_and_normalises_month(self):
        _mock_page(
            [
                {
                    "pk": 11,
                    "title": "CDI 2025-07",
                    "date": "2025-07-31T00:00:00Z",
                    "created": "2025-07-15T12:00:00Z",
                    "subtype": "raster",
                    "filesize": 2048,
                    "detail_url": "https://geonode.com/d/11",
                },
                # invalid date -> skipped, not written
                {"pk": 12, "title": "bad", "date": "not-a-date"},
            ],
            total=2,
        )
        call_command(
            "sync_publication_geonodes", "--category", CDIGeonodeCategory.cdi
        )

        self.assertEqual(PublicationGeonode.objects.count(), 1)
        row = PublicationGeonode.objects.get(geonode_id=11)
        # save() normalises resource date to first-of-month
        self.assertEqual(str(row.year_month), "2025-07-01")
        self.assertEqual(row.file_size, 2048)

        # second run updates the same row, not a duplicate
        _mock_page(
            [{
                "pk": 11,
                "title": "CDI 2025-07 updated",
                "date": "2025-07-31T00:00:00Z",
            }],
            total=1,
        )
        call_command(
            "sync_publication_geonodes", "--category", CDIGeonodeCategory.cdi
        )
        self.assertEqual(PublicationGeonode.objects.count(), 1)
        row.refresh_from_db()
        self.assertEqual(row.title, "CDI 2025-07 updated")

    def test_dry_run_writes_nothing(self):
        _mock_page(
            [{"pk": 11, "title": "x", "date": "2025-07-15T00:00:00Z"}],
            total=1,
        )
        call_command(
            "sync_publication_geonodes",
            "--category", CDIGeonodeCategory.cdi,
            "--dry-run",
        )
        self.assertEqual(PublicationGeonode.objects.count(), 0)

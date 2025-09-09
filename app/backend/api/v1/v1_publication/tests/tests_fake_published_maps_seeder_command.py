from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from io import StringIO
from api.v1.v1_publication.models import (
    Publication,
    PublicationStatus,
)


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    GEONODE_BASE_URL="http://geonode:8000",
    GEONODE_ADMIN_USERNAME="admin",
    GEONODE_ADMIN_PASSWORD="admin",
)
class FakePublishedMapsSeederCommandTestCase(TestCase):
    def setUp(self):
        call_command("fake_users_seeder", "--test", True)
        self.mock_response_data = {
            "total": 6,
            "resources": [
                {
                    "pk": 1,
                    "date": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 1",
                },
                {
                    "pk": 2,
                    "date": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 2",
                },
                {
                    "pk": 3,
                    "date": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 3",
                },
                {
                    "pk": 4,
                    "date": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 4",
                },
                {
                    "pk": 5,
                    "date": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 5",
                },
                {
                    "pk": 6,
                    "date": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 6",
                },
            ]
        }

    @patch("requests.get")
    def test_run_fake_published_maps_seeder(self, mock_get):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        call_command("fake_published_maps_seeder")

        total_published = Publication.objects.filter(
            status=PublicationStatus.published
        ).count()
        self.assertEqual(total_published, 6)

    @patch("requests.get")
    def test_geonode_server_is_error(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.json.return_value = {
            "total": 0,
            "resources": [],
            "failed": "Error fetching Rundeck projects."
        }

        out = StringIO()
        with patch('sys.stdout', new=out):
            call_command("fake_published_maps_seeder")
            output = out.getvalue()

        self.assertIn(
            "Failed to fetch data from GeoNode API.Status code: 500",
            output
        )

        # Verify no publications were created
        total_published = Publication.objects.filter(
            status=PublicationStatus.published
        ).count()
        self.assertEqual(total_published, 0)

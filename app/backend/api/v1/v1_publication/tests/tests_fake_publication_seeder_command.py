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
class FakePublicationsSeederCommandTestCase(TestCase):
    def setUp(self):
        call_command("fake_users_seeder", "--test", True, "--repeat", 2)
        self.mock_response_data = {
            "total": 6,
            "resources": [
                {
                    "pk": 1,
                    "created": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 1",
                },
                {
                    "pk": 2,
                    "created": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 2",
                },
                {
                    "pk": 3,
                    "created": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 3",
                },
                {
                    "pk": 4,
                    "created": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 4",
                },
                {
                    "pk": 5,
                    "created": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 5",
                },
                {
                    "pk": 6,
                    "created": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 6",
                },
            ]
        }

    @patch("requests.get")
    def test_run_fake_publications_seeder(self, mock_get):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        call_command("fake_publications_seeder")
        total_in_review = Publication.objects.filter(
            status=PublicationStatus.in_review
        ).count()
        self.assertEqual(total_in_review, 3)
        total_in_validation = Publication.objects.filter(
            status=PublicationStatus.in_validation
        ).count()
        self.assertEqual(total_in_validation, 3)
        total_published = Publication.objects.filter(
            status=PublicationStatus.published
        ).count()
        self.assertEqual(total_published, 0)

    @patch("requests.get")
    def test_max_repeat_fake_publications_seeder(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        out = StringIO()
        with patch('sys.stdout', new=out):
            call_command("fake_publications_seeder", "--repeat", 7)
            output = out.getvalue()

        self.assertIn(
            "The maximum number of publications to create is 6",
            output
        )

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
            call_command("fake_publications_seeder")
            output = out.getvalue()

        self.assertIn(
            "Unable to fetch CDI Geonode IDs",
            output
        )

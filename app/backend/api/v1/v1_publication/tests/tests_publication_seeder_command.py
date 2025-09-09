from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from io import StringIO
from datetime import datetime, timedelta
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.constants import (
    PublicationStatus,
    CDIGeonodeCategory,
)
from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    GEONODE_BASE_URL="http://geonode:8000",
    GEONODE_ADMIN_USERNAME="admin",
    GEONODE_ADMIN_PASSWORD="admin",
)
class PublicationsSeederCommandTestCase(TestCase):
    def setUp(self):
        # Counter to ensure unique task IDs across all tests
        self._task_id_counter = 0

        def generate_task_id(*args, **kwargs):
            self._task_id_counter += 1
            return f"mock-task-id-{self._task_id_counter}"

        self.generate_task_id = generate_task_id
        self.mock_response_data = {
            "total": 6,
            "page_size": 20,
            "resources": [
                {
                    "pk": 1,
                    "date": "2024-12-27T02:24:28Z",
                    "title": "CDI raster 1",
                    "download_url": "http://geonode:8000/download/1",
                },
                {
                    "pk": 2,
                    "date": "2024-11-15T10:30:00Z",
                    "title": "CDI raster 2",
                    "download_url": "http://geonode:8000/download/2",
                },
                {
                    "pk": 3,
                    "date": "2024-10-10T15:45:00Z",
                    "title": "CDI raster 3",
                    "download_url": "http://geonode:8000/download/3",
                },
                {
                    "pk": 4,
                    "date": "2024-09-05T08:20:00Z",
                    "title": "CDI raster 4",
                    "download_url": "http://geonode:8000/download/4",
                },
                {
                    "pk": 5,
                    "date": "2024-08-20T12:15:00Z",
                    "title": "CDI raster 5",
                    "download_url": "http://geonode:8000/download/5",
                },
                {
                    "pk": 6,
                    "date": "2024-07-30T09:30:00Z",
                    "title": "CDI raster 6",
                    "download_url": "http://geonode:8000/download/6",
                },
            ]
        }

        self.mock_empty_response = {
            "total": 0,
            "page_size": 20,
            "resources": []
        }

    @patch("django_q.tasks.async_task")
    @patch("requests.get")
    def test_run_publications_seeder(self, mock_get, mock_async_task):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data
        mock_async_task.side_effect = self.generate_task_id

        call_command("publications_seeder")

        # Test that all publications are created with published status
        total_publications = Publication.objects.count()
        self.assertEqual(total_publications, 6)

        # Test that all publications have published status
        total_published = Publication.objects.filter(
            status=PublicationStatus.published
        ).count()
        self.assertEqual(total_published, 6)

        # Test that jobs are created for each publication
        total_jobs = Jobs.objects.filter(
            type=JobTypes.download_geonode_dataset
        ).count()
        self.assertEqual(total_jobs, 6)

        # Test specific publication data
        publication = Publication.objects.filter(cdi_geonode_id=1).first()
        self.assertIsNotNone(publication)
        expected_date = "2024-12-01"
        self.assertEqual(
            publication.year_month.strftime("%Y-%m-%d"), expected_date
        )
        self.assertEqual(publication.status, PublicationStatus.published)
        self.assertEqual(publication.initial_values, {})

    @patch("django_q.tasks.async_task")
    @patch("requests.get")
    def test_publications_seeder_with_category_argument(
        self, mock_get, mock_async_task
    ):
        # Test with different category
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data
        mock_async_task.side_effect = self.generate_task_id

        call_command(
            "publications_seeder", "--category", CDIGeonodeCategory.spi
        )

        # Verify the correct URL was called with the category parameter
        expected_url = (
            "http://geonode:8000/api/v2/resources"
            f"?filter{{category.identifier}}={CDIGeonodeCategory.spi}"
            "&filter{subtype}=raster&page=1&sort[]=-date"
        )
        mock_get.assert_called_with(
            expected_url,
            auth=("admin", "admin")
        )

    @patch("django_q.tasks.async_task")
    @patch("requests.get")
    def test_existing_publication_update(self, mock_get, mock_async_task):
        # Create an existing publication without validated_values
        existing_publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2024-12-01",
            initial_values={"test": "data"},
            due_date="2025-01-01",
            status=PublicationStatus.in_review
        )

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data
        mock_async_task.side_effect = self.generate_task_id

        out = StringIO()
        with patch('sys.stdout', new=out):
            call_command("publications_seeder")
            output = out.getvalue()

        # Check that warning about existing publication is shown
        self.assertIn(
            "Publication with cdi_geonode_id 1 already exists. Skipping.",
            output
        )

        # Verify the existing publication was updated with validated_values
        existing_publication.refresh_from_db()
        expected_values = {"test": "data"}
        self.assertEqual(
            existing_publication.validated_values, expected_values
        )
        self.assertEqual(existing_publication.narrative, "")
        self.assertIsNotNone(existing_publication.published_at)

        # Only 5 new publications should be created (excluding existing)
        total_publications = Publication.objects.count()
        self.assertEqual(total_publications, 6)

    @patch("requests.get")
    def test_geonode_server_error_response(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.json.return_value = {
            "total": 0,
            "resources": [],
            "error": "Internal server error"
        }

        out = StringIO()
        with patch('sys.stdout', new=out):
            call_command("publications_seeder")
            output = out.getvalue()

        self.assertIn("Failed to fetch page 1: 500", output)

        # No publications should be created
        total_publications = Publication.objects.count()
        self.assertEqual(total_publications, 0)

    @patch("django_q.tasks.async_task")
    @patch("requests.get")
    def test_pagination_handling(self, mock_get, mock_async_task):
        # Mock first page response
        first_page_data = {
            "total": 25,
            "page_size": 20,
            "resources": [
                {
                    "pk": i,
                    "date": "2024-12-01T00:00:00Z",
                    "title": f"CDI raster {i}",
                    "download_url": f"http://geonode:8000/download/{i}",
                }
                for i in range(1, 21)  # 20 resources
            ]
        }

        # Mock second page response
        second_page_data = {
            "total": 25,
            "page_size": 20,
            "resources": [
                {
                    "pk": i,
                    "date": "2024-12-01T00:00:00Z",
                    "title": f"CDI raster {i}",
                    "download_url": f"http://geonode:8000/download/{i}",
                }
                for i in range(21, 26)  # 5 resources
            ]
        }

        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: first_page_data),
            MagicMock(status_code=200, json=lambda: second_page_data),
        ]
        mock_async_task.side_effect = self.generate_task_id

        call_command("publications_seeder")

        # Verify pagination calls were made
        self.assertEqual(mock_get.call_count, 2)

        # Check first page URL
        first_call_url = mock_get.call_args_list[0][0][0]
        self.assertIn("page=1", first_call_url)

        # Check second page URL
        second_call_url = mock_get.call_args_list[1][0][0]
        self.assertIn("page=2", second_call_url)

        # All 25 publications should be created
        total_publications = Publication.objects.count()
        self.assertEqual(total_publications, 25)

    @patch("django_q.tasks.async_task")
    @patch("requests.get")
    def test_date_parsing_and_due_date_calculation(
        self, mock_get, mock_async_task
    ):
        mock_response_data = {
            "total": 2,
            "page_size": 20,
            "resources": [
                {
                    "pk": 1,
                    "date": "2024-06-15T10:30:00Z",
                    "title": "CDI raster with valid date",
                    "download_url": "http://geonode:8000/download/1",
                },
                {
                    "pk": 2,
                    "date": "2024-01-01T00:00:00Z",
                    "title": "CDI raster with invalid date",
                    "download_url": "http://geonode:8000/download/2",
                },
            ]
        }

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response_data
        mock_async_task.side_effect = self.generate_task_id

        call_command("publications_seeder")

        # Test publication with valid date
        pub_valid_date = Publication.objects.filter(cdi_geonode_id=1).first()
        self.assertIsNotNone(pub_valid_date)
        expected_date = "2024-06-01"
        self.assertEqual(
            pub_valid_date.year_month.strftime("%Y-%m-%d"), expected_date
        )
        # Due date should be 30 days after the date
        base_date = datetime.strptime("2024-06-15", "%Y-%m-%d")
        expected_due_date = base_date + timedelta(days=30)
        self.assertEqual(pub_valid_date.due_date, expected_due_date.date())

        # Test publication with second valid date
        pub_second_date = Publication.objects.filter(cdi_geonode_id=2).first()
        self.assertIsNotNone(pub_second_date)
        expected_date = "2024-01-01"
        self.assertEqual(
            pub_second_date.year_month.strftime("%Y-%m-%d"), expected_date
        )
        # Due date should be 30 days after January 1st, 2024
        base_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        expected_due_date = base_date + timedelta(days=30)
        self.assertEqual(pub_second_date.due_date, expected_due_date.date())

    @patch("django_q.tasks.async_task")
    @patch("requests.get")
    def test_job_creation_details(self, mock_get, mock_async_task):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "total": 1,
            "page_size": 20,
            "resources": [
                {
                    "pk": 123,
                    "date": "2024-12-01T00:00:00Z",
                    "title": "Test CDI raster",
                    "download_url": "http://geonode:8000/download/123",
                }
            ]
        }
        mock_async_task.side_effect = self.generate_task_id

        with patch('time.time', return_value=1234567890):
            call_command("publications_seeder")

        # Check job was created with correct details
        job = Jobs.objects.filter(
            type=JobTypes.download_geonode_dataset
        ).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.status, JobStatus.on_progress)
        # Check that task_id was set to the generated value
        self.assertTrue(job.task_id.startswith("mock-task-id-"))

        # Check job info
        expected_filename = "raster_123_1234567890.tif"
        self.assertEqual(job.info["filename"], expected_filename)
        self.assertTrue(job.info["is_seeder"])
        self.assertIsNone(job.info["subject"])
        self.assertIsNone(job.info["message"])

    @patch("requests.get")
    def test_empty_resources_response(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_empty_response

        call_command("publications_seeder")

        # No publications should be created
        total_publications = Publication.objects.count()
        self.assertEqual(total_publications, 0)

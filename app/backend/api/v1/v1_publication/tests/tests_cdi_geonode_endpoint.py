from rest_framework.test import APITestCase
from rest_framework import status
from django.core.management import call_command
from unittest.mock import patch
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.models import Publication, PublicationStatus
from api.v1.v1_publication.constants import DroughtCategory, CDIGeonodeCategory


class CDIGeonodeAPITestCase(APITestCase):
    def setUp(self):
        self.url = "/api/v1/admin/cdi-geonode"
        call_command(
            "generate_admin_seeder", "--test", True
        )

        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).order_by("?").first()
        self.client.force_authenticate(user=self.user)

        # Mock response data from the external API
        resources = [
            {
                "pk": 1,
                "title": "Test GeoNode Resource",
                "detail_url": "https://geonode.com/catalogue/#/dataset/1",
                "embed_url": "https://geonode.com/datasets/geonode:test/embed",
                "thumbnail_url": (
                    "https://geonode.com/uploaded/thumbs/dataset-3d6e57f3.jpg"
                ),
                "download_url": (
                    "https://geonode.com/datasets/geonode:test"
                    "/dataset_download"
                ),
                "created": "2025-01-15T12:00:00Z",
                "date": "2024-12-31T12:00:00Z",
            },
            {
                "pk": 2,
                "title": "Another Resource",
                "detail_url": "http://geonode.com/catalogue/#/dataset/2",
                "embed_url": "http://geonode.com/datasets/geonode:test/embed",
                "thumbnail_url": (
                    "https://geonode.com/uploaded/thumbs/dataset-3d6e89i1.jpg"
                ),
                "download_url": (
                    "https://geonode.com/datasets/geonode:another"
                    "/dataset_download"
                ),
                "created": "2025-01-16T14:00:00Z",
                "date": "2024-11-31T16:00:00Z",
            },
        ]
        self.mock_response_data = {
            "total": 2,
            "page": 1,
            "page_size": 10,
            "resources": resources
        }

    @patch("requests.get")  # Mock the requests.get call
    def test_get_cdi_geonode_success(self, mock_get):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["data"][0]["pk"], 1)
        self.assertEqual(
            response.data["data"][0]["title"],
            "Test GeoNode Resource"
        )
        self.assertEqual(
            response.data["data"][0]["detail_url"],
            "https://geonode.com/catalogue/#/dataset/1"
        )
        self.assertEqual(
            response.data["data"][0]["created"],
            "2025-01-15T12:00:00Z"
        )

    @patch("requests.get")
    def test_get_cdi_geonode_error(self, mock_get):
        # Configure the mock to return an error response
        mock_get.return_value.status_code = 500

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.data,
            {"message": "Server Error: Unable to fetch data."}
        )

    @patch("requests.get")
    def test_get_by_unauthenticated_user(self, _):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @patch("requests.get")
    def test_publication_exists(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2024-12-01",
            due_date="2025-01-31",
            initial_values=[{
                "administration_id": 1,
                "value": 6,
                "category": DroughtCategory.d3
            }]
        )

        # Perform the GET request
        response = self.client.get(
            f"{self.url}?status={PublicationStatus.in_review}"
            f"&category={CDIGeonodeCategory.cdi}"
        )

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"][0]["publication_id"],
            publication.pk
        )
        self.assertEqual(
            response.data["data"][0]["year_month"].strftime("%Y-%m-%d"),
            "2024-12-01"
        )
        self.assertEqual(
            response.data["data"][0]["status"],
            PublicationStatus.in_review
        )

    @patch("requests.get")
    def test_empty_results_publication_filtering_by_status(self, mock_get):
        resources = Publication.objects.filter(
            status=PublicationStatus.in_validation
        )
        data = [
            {
                "pk": r.cdi_geonode_id,
                "title": "Test GeoNode Resource",
                "detail_url": (
                    f"https://geonode.com/catalogue/#/dataset/{r.cdi_geonode_id}"
                ),
                "embed_url": "https://geonode.com/datasets/geonode:test/embed",
                "thumbnail_url": (
                    "https://geonode.com/uploaded/thumbs/dataset-3d6e57f3.jpg"
                ),
                "download_url": (
                    "https://geonode.com/datasets/geonode:test"
                    "/dataset_download"
                ),
                "created": "2025-01-15T12:00:00Z",
                "date": "2024-12-31T12:00:00Z",
            }
            for r in resources
        ]
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "total": resources.count(),
            "page": 1,
            "page_size": 10,
            "resources": data
        }

        Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2024-12-01",
            due_date="2025-01-31",
            initial_values=[{
                "administration_id": 1,
                "value": 6,
                "category": DroughtCategory.d3
            }]
        )

        response = self.client.get(
            f"{self.url}?status={PublicationStatus.in_validation}"
            f"&category={CDIGeonodeCategory.cdi}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["total"],
            0
        )

    @patch("requests.get")
    def test_get_cdi_geonode_bad_request(self, mock_get):
        mock_get.return_value.status_code = 400
        mock_get.return_value.json.return_value = self.mock_response_data

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"message": "Bad Request: Invalid parameters."}
        )

    @patch("requests.get")
    def test_get_cdi_geonode_with_invalid_category(self, _):
        response = self.client.get(
            f"{self.url}?category=invalid"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"message": "Invalid category parameter."}
        )

    @patch("requests.get")
    def test_get_cdi_geonode_details(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "resource": {
                "pk": "7",
                "title": "cdi_202501",
                "date": "2025-01-17T02:31:00Z",
                "is_approved": True,
                "detail_url": "https://geonode.com/catalogue/#/dataset/7",
                "embed_url": (
                    "https://geonode.com/datasets/"
                    "geonode:cdi_202501/embed"
                ),
                "thumbnail_url": (
                    "https://geonode.com/uploaded/thumbs/dataset-3d6e57f3.jpg"
                ),
                "created": "2025-01-17T02:31:05.539148Z",
                "download_url": (
                    "https://geonode.com/datasets/"
                    "geonode:cdi_202501/dataset_download"
                ),
            }
        }
        response = self.client.get(
            f"{self.url}?id=7"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.data),
            [
                "pk",
                "title",
                "detail_url",
                "embed_url",
                "thumbnail_url",
                "download_url",
                "created",
                "year_month",
                "publication_id",
                "status",
            ]
        )

    @patch("requests.get")
    def test_get_cdi_geonode_details_with_invalid_id(self, mock_get):
        mock_get.return_value.status_code = 500
        response = self.client.get(
            f"{self.url}?id=9999"
        )
        self.assertEqual(response.status_code, 500)

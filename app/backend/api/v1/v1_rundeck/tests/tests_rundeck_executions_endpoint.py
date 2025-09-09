from rest_framework.test import APITestCase
from rest_framework import status
from django.core.management import call_command
from django.urls import reverse
from django.test.utils import override_settings
from unittest.mock import patch
from api.v1.v1_users.models import SystemUser, UserRoleTypes


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    RUNDECK_API_URL="http://rundeck:4440/api/50",
    RUNDECK_API_TOKEN="test-token",
)
class RundeckExecutionsAPITestCase(APITestCase):
    def setUp(self):
        call_command("generate_admin_seeder", "--test", True)

        self.user = (
            SystemUser.objects.filter(
                role=UserRoleTypes.admin
            ).order_by("?").first()
        )
        self.client.force_authenticate(user=self.user)

        # Mock response data from the external API
        self.mock_response_data = {
            "paging": {
                "count": 4,
                "total": 4,
                "offset": 0,
                "max": 20
            },
            "executions": [
                {
                    "id": 155,
                    "href": "/api/50/execution/142",
                    "permalink": "/project/drought_map_hub/execution/show/142",
                    "status": "running",
                    "project": "drought_map_hub",
                    "executionType": "user",
                    "user": "admin",
                    "date-started": {
                        "unixtime": 1739849217872,
                        "date": "2025-02-18T03:26:57Z"
                    },
                    "job": {
                        "id": "34afdb08-3089-4c9c-9cc3-89c148110d5d",
                        "options": {
                            "year_month": "2025-02"
                        },
                    }
                },
                {
                    "id": 150,
                    "href": "/api/50/execution/150",
                    "permalink": "/project/drought_map_hub/execution/show/150",
                    "status": "succeeded",
                    "project": "drought_map_hub",
                    "executionType": "user",
                    "user": "admin",
                    "date-started": {
                        "unixtime": 1739850902867,
                        "date": "2025-02-18T03:55:02Z"
                    },
                    "date-ended": {
                        "unixtime": 1739851038507,
                        "date": "2025-02-18T03:57:18Z"
                    },
                    "job": {
                        "id": "34afdb08-3089-4c9c-9cc3-89c148110d5d",
                        "options": {
                            "year_month": "2025-01"
                        },
                    }
                },
                {
                    "id": 146,
                    "href": "/api/50/execution/146",
                    "permalink": "/project/drought_map_hub/execution/show/146",
                    "status": "failed",
                    "project": "drought_map_hub",
                    "executionType": "user",
                    "user": "admin",
                    "date-started": {
                        "unixtime": 1739849509760,
                        "date": "2025-02-18T03:31:49Z"
                    },
                    "date-ended": {
                        "unixtime": 1739849645859,
                        "date": "2025-02-18T03:34:05Z"
                    },
                    "job": {
                        "id": "34afdb08-3089-4c9c-9cc3-89c148110d5d",
                        "options": {
                            "year_month": "2024-12"
                        },
                    }
                }
            ]
        }
        self.url = reverse(
            "rundeck-executions",
            kwargs={
                "version": "v1",
                "job_id": "34afdb08-3089-4c9c-9cc3-89c148110d5d",
            }
        )

    @patch("requests.get")  # Mock the requests.get call
    def test_get_rundeck_executions_success(self, mock_get):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(response.data),
            ["current", "total", "total_page", "data"]
        )
        self.assertEqual(
            len(response.data["data"]),
            len(self.mock_response_data["executions"])
        )
        self.assertEqual(
            list(response.data["data"][0]),
            [
                "id",
                "permalink",
                "status",
                "date_started",
                "date_ended",
                "year_month",
            ]
        )

    @patch("requests.get")
    def test_get_rundeck_executions_error(self, mock_get):
        # Configure the mock to return a response with an error status code
        mock_get.return_value.status_code = 500
        mock_response = {
            "paging": {
                "count": 0,
                "total": 0,
                "offset": 0,
                "max": 20
            },
            "executions": [],
        }
        mock_get.return_value.json.return_value = mock_response

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertEqual(
            response.data,
            {"current": 0, "data": [], "total": 0, "total_page": 20}
        )

    @patch("requests.post")  # Mock the requests.get post
    def test_rundeck_execute_job_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = \
            self.mock_response_data["executions"][0]

        # Perform the POST request
        response = self.client.post(
            self.url,
            {
                "year_month": "2025-02",
                "lst_weight": 0.3,
                "ndvi_weight": 0.3,
                "spi_weight": 0.4,
                "sm_weight": 0.0,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["id"],
            self.mock_response_data["executions"][0]["id"]
        )

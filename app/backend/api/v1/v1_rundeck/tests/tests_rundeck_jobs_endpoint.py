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
class RundeckJobsAPITestCase(APITestCase):
    def setUp(self):
        call_command("generate_admin_seeder", "--test", True)

        self.user = (
            SystemUser.objects.filter(
                role=UserRoleTypes.admin
            ).order_by("?").first()
        )
        self.client.force_authenticate(user=self.user)

        # Mock response data from the external API
        self.mock_response_data = [
            {
                "id": "34afdb08-3089-4c9c",
                "serverNodeUUID": "a14bc3e6-75e8-4fe4-a90d-a16dcc976bf6",
                "permalink": "/drought_map_hub/job/show/34afdb08-3089-4c9c",
                "name": "cdi_automation",
                "project": "drought_map_hub",
            }
        ]
        self.url = reverse(
            "rundeck-jobs",
            kwargs={
                "version": "v1",
                "project": "drought_map_hub"
            }
        )

    @patch("requests.get")  # Mock the requests.get call
    def test_get_rundeck_jobs_success(self, mock_get):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 1
        )
        self.assertEqual(
            response.data[0]["id"],
            self.mock_response_data[0]["id"]
        )
        self.assertEqual(
            list(response.data[0]),
            ["id", "name", "permalink"]
        )

    @patch("requests.get")
    def test_get_rundeck_jobs_error(self, mock_get):
        # Configure the mock to return a response with an error status code
        mock_get.return_value.status_code = 500
        mock_response = {"failed": "Error fetching Rundeck jobs."}
        mock_get.return_value.json.return_value = mock_response

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertEqual(response.data, mock_response)

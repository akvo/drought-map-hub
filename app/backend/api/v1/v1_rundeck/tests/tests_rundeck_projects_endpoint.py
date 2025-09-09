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
class RundeckProjectsAPITestCase(APITestCase):
    def setUp(self):
        call_command(
            "generate_admin_seeder", "--test", True
        )

        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).order_by("?").first()
        self.client.force_authenticate(user=self.user)

        # Mock response data from the external API
        self.mock_response_data = [
            {
                "url": "http://localhost:4440/api/50/project/drought_map_hub",
                "name": "drought_map_hub",
                "description": "",
                "label": "Eswatini Drought Map Hub",
                "created": "2024-12-27T02:24:28Z"
            }
        ]
        self.url = reverse(
            "rundeck-projects",
            kwargs={"version": "v1"}
        )

    @patch("requests.get")  # Mock the requests.get call
    def test_get_rundeck_projects_success(self, mock_get):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            [{'name': 'drought_map_hub', 'label': 'Eswatini Drought Map Hub'}]
        )

    @patch("requests.get")
    def test_get_rundeck_projects_error(self, mock_get):
        # Configure the mock to return a response with an error status code
        mock_get.return_value.status_code = 500
        mock_response = {
            "failed": "Error fetching Rundeck projects."
        }
        mock_get.return_value.json.return_value = mock_response

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertEqual(response.data, mock_response)

from django.urls import reverse
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from api.v1.v1_rundeck.models import Settings
from api.v1.v1_users.models import SystemUser as User


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    RUNDECK_API_URL="http://rundeck:4440/api/50",
    RUNDECK_API_TOKEN="test-token",
)
class SettingsViewSetTests(APITestCase):

    def setUp(self):
        """Set up test users and a sample Settings instance."""
        self.admin_user = User.objects.create_superuser(
            name="admin", email="admin@example.com", password="adminpass"
        )
        self.regular_user = User.objects._create_user(
            name="user", email="user@example.com", password="userpass"
        )

        self.settings = Settings.objects.create(
            project_name="drought_map_hub-automation",
            job_id="34afdb08-3089-4c9c-9cc3-89c148110d5d",
            on_success_emails=["success@example.com"],
            on_failure_emails=["failure@example.com"],
            on_exceeded_emails=["exceeded@example.com"],
        )

        self.settings_url = reverse(
            "settings",
            kwargs={
                "version": "v1",
            }
        )  # URL for list and create
        self.detail_url = reverse(
            "settings-details",
            kwargs={
                "version": "v1",
                "pk": self.settings.pk
            }
        )  # Detail URL

        self.mock_config = {
            "id": "34afdb08-3089-4c9c-9cc3-89c148110d5d",
            "name": "cdi_automation",
            "notification": {
                "onavgduration": {
                    "email": {
                        "recipients": "test@example.com",
                        "subject": "Job Exceeded average duration"
                    }
                },
                "onfailure": {
                    "email": {
                        "attachLog": True,
                        "attachLogInFile": True,
                        "recipients": "shirley@example.com",
                        "subject": "CDI-E Automation - Error"
                    }
                },
                "onsuccess": {
                    "email": {
                        "attachLog": True,
                        "attachLogInFile": True,
                        "recipients": "iwan@akvo.org",
                        "subject": "CDI-E Automation - Success"
                    }
                }
            },
            "notifyAvgDurationThreshold": "+30",
            "options": [
                {
                    "dateFormat": "YYYY-MM",
                    "isDate": True,
                    "label": "Year Month",
                    "name": "year_month",
                    "value": "${DATE:YYYY-MM}"
                }
            ],
            "plugins": {
                "ExecutionLifecycle": {}
            },
            "scheduleEnabled": True,
            "sequence": {
                "commands": [
                    {
                        "exec": "/src/background-job/job.sh"
                    }
                ],
                "keepgoing": False,
                "strategy": "node-first"
            },
            "uuid": "34afdb08-3089-4c9c-9cc3-89c148110d5d"
        }

    def test_admin_can_list_settings(self):
        """Admin users should be able to list settings."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_list_settings(self):
        """Non-admin users should not be able to list settings."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_list_settings(self):
        """Anonymous users should not be able to list settings."""
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_settings(self):
        """Admin users should be able to create settings."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "project_name": "New Project",
            "job_id": "34afdb08-3089-4c9c-9cc3-89c148110d5d",
        }
        response = self.client.post(self.settings_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Settings.objects.count(), 2)

    def test_non_admin_cannot_create_settings(self):
        """Non-admin users should not be able to create settings."""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "project_name": "New Project",
            "job_id": "67890",
            "on_success_emails": ["new_success@example.com"],
            "on_failure_emails": ["new_failure@example.com"],
        }
        response = self.client.post(self.settings_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("requests.get")
    @patch("requests.delete")
    @patch("requests.post")
    def test_admin_can_update_settings(self, mock_post, mock_delete, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [self.mock_config]
        mock_delete.return_value.status_code = 204
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.mock_config

        """Admin users should be able to update settings."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "on_success_emails": ["updated_success@example.com"],
            "on_failure_emails": ["updated_failure@example.com"],
            "on_exceeded_emails": ["updated_exceeded@example.com"],
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.settings.refresh_from_db()
        self.assertEqual(
            self.settings.on_success_emails, ["updated_success@example.com"]
        )
        self.assertEqual(
            self.settings.on_failure_emails, ["updated_failure@example.com"]
        )
        self.assertEqual(
            self.settings.on_exceeded_emails, ["updated_exceeded@example.com"]
        )
        self.assertEqual(self.settings.job_config, self.mock_config)

    def test_non_admin_cannot_update_settings(self):
        """Non-admin users should not be able to update settings."""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "project_name": "Unauthorized Update",
            "job_id": "99999",
            "on_success_emails": ["updated_success@example.com"],
            "on_failure_emails": ["updated_failure@example.com"],
            "on_exceeded_emails": ["updated_exceeded@example.com"],
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_settings(self):
        """Admin users should be able to delete settings."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Settings.objects.count(), 0)

    def test_non_admin_cannot_delete_settings(self):
        """Non-admin users should not be able to delete settings."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

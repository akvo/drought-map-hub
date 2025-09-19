from rest_framework.test import APITestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from pathlib import Path
from api.v1.v1_setup.models import Organization, SiteConfig


@override_settings(USE_TZ=False, TEST_ENV=True)
class UpdateAppAPITest(APITestCase):

    def setUp(self) -> None:
        """
        Set up the test environment.
        """
        # Create a sample SiteConfig instance
        self.app = SiteConfig.objects.create(name="Test Site")

        self.url = reverse("manage_setup", kwargs={
            "version": "v1",
            "pk": self.app.id
        })

        # Create a sample Organization instance
        Organization.objects.create(
            name="Test Organization",
            website="https://www.testorg.com",
            logo="organization_logos/test_logo.jpg",
            is_twg=True,
            is_collaborator=False
        )
        Organization.objects.create(
            name="Another Organization",
            website="https://www.anotherorg.com",
            logo="organization_logos/another_logo.jpg",
            is_twg=False,
            is_collaborator=True
        )
        self.path = Path(__file__).resolve().parent
        self.org_image_1 = (
            self.path / "static/logo-test.jpg"
        )
        self.org_image_2 = (
            self.path / "static/logo-test.jpg"
        )
        self.geojson_file = (
            self.path / "static/administrations.geojson"
        )
        return super().setUp()

    def test_update_app_info_without_uploads(self):
        """
        Test the app endpoint for updating app information.
        """
        data = {
            "name": "Updated Test Site",
            "organizations[0][name]": "Updated Test Organization",
            "organizations[0][website]": "https://www.updatedtestorg.com",
            "organizations[0][is_twg]": False,
            "organizations[0][is_collaborator]": True,
            "organizations[1][name]": "New Organization",
            "organizations[1][website]": "https://www.neworg.com",
            "organizations[1][is_twg]": True,
            "organizations[1][is_collaborator]": False,
        }
        response = self.client.put(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("name", response.data)
        self.assertIn("organizations", response.data)
        self.assertEqual(len(response.data["organizations"]), 2)
        self.assertEqual(
            response.data["name"], "Updated Test Site"
        )
        org_names = [org["name"] for org in response.data["organizations"]]
        self.assertIn("Updated Test Organization", org_names)
        self.assertIn("New Organization", org_names)

    def test_update_app_info_with_uploads(self):
        """
        Test the app endpoint for updating app information with file uploads.
        """
        with (
            open(self.org_image_1, 'rb') as img1,
            open(self.geojson_file, 'rb') as geojson
        ):
            data = {
                "name": "Updated Test Site with Uploads",
                "organizations[0][name]": "Updated Test Organization w Logo",
                "organizations[0][website]": "https://updatedtestorgwlogo.com",
                "organizations[0][is_twg]": True,
                "organizations[0][is_collaborator]": False,
                "organizations[0][logo]": img1,
                "geojson_file": geojson,
            }
            response = self.client.put(self.url, data, format='multipart')

        if response.status_code != status.HTTP_200_OK:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("name", response.data)
        self.assertIn("organizations", response.data)
        self.assertEqual(len(response.data["organizations"]), 1)
        self.assertEqual(
            response.data["name"], "Updated Test Site with Uploads"
        )
        org_names = [org["name"] for org in response.data["organizations"]]
        self.assertIn("Updated Test Organization w Logo", org_names)
        # Check if logos are included in the response
        for org in response.data["organizations"]:
            self.assertIsNotNone(org.get("logo"))

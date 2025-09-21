from rest_framework.test import APITestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from api.v1.v1_setup.models import Organization, SiteConfig


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    SETUP_SECRET_KEY="test-secret-key"
)
class GetAppAPITest(APITestCase):

    def setUp(self) -> None:
        """
        Set up the test environment.
        """
        self.url = reverse("setup", kwargs={"version": "v1"})
        # Create a sample SiteConfig instance
        SiteConfig.objects.create(name="Test Site")
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
        return super().setUp()

    def test_get_app_info(self):
        """
        Test the app endpoint for retrieving app information.
        """
        response = self.client.get(
            self.url,
            HTTP_X_SETUP_SECRET="test-secret-key",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("name", response.data)
        self.assertIn("organizations", response.data)
        self.assertEqual(len(response.data["organizations"]), 2)
        self.assertEqual(
            response.data["name"], "Test Site"
        )
        org_names = [org["name"] for org in response.data["organizations"]]
        self.assertIn("Test Organization", org_names)
        self.assertIn("Another Organization", org_names)

    def test_no_site_config(self):
        """
        Test the app endpoint when no SiteConfig exists.
        """
        # Delete all SiteConfig instances
        SiteConfig.objects.all().delete()
        response = self.client.get(
            self.url,
            HTTP_X_SETUP_SECRET="test-secret-key",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"], "Site configuration not found."
        )

from rest_framework.test import APITestCase
from pathlib import Path
from django.urls import reverse
from django.test.utils import override_settings
from rest_framework import status
from api.v1.v1_setup.models import Organization, SiteConfig


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    SETUP_SECRET_KEY="test-secret-key"
)
class SetupAppAPITest(APITestCase):

    def setUp(self) -> None:
        """
        Set up the test environment.
        """
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

    def test_successful_setup(self):
        """
        Test the setup endpoint for successful setup.
        """
        url = reverse("setup", kwargs={"version": "v1"})
        data = {
            "name": "New Drought Map Hub",
            "geojson_file": self.geojson_file.open("rb"),
        }
        # Add organizations as separate fields for multipart form
        data["organizations[0][name]"] = "Organization 1"
        data["organizations[0][website]"] = "https://www.organization1.com"
        data["organizations[0][is_twg]"] = "true"
        data["organizations[0][is_collaborator]"] = "false"
        # Skip logo for now due to image format issues
        data["organizations[0][logo]"] = self.org_image_1.open("rb")

        data["organizations[1][name]"] = "Organization 2"
        data["organizations[1][website]"] = "https://www.organization2.com"
        data["organizations[1][is_twg]"] = "false"
        data["organizations[1][is_collaborator]"] = "true"
        # Skip logo for now due to image format issues
        data["organizations[1][logo]"] = self.org_image_2.open("rb")
        response = self.client.post(
            url,
            data,
            format="multipart",
            HTTP_X_SETUP_SECRET="test-secret-key",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify that file uploads are handled correctly
        self.assertIn("geojson_file", response.data)
        self.assertEqual(
            response.data["geojson_file"],
            "administrations.geojson"
        )

        self.assertIn("organizations", response.data)
        self.assertEqual(len(response.data["organizations"]), 2)

        for org in response.data["organizations"]:
            self.assertIn("logo", org)
            self.assertTrue(org["logo"].startswith("/media/"))
        # Close the opened files
        data["geojson_file"].close()
        data["organizations[0][logo]"].close()
        data["organizations[1][logo]"].close()

        # Verify uuid is returned
        self.assertIn("uuid", response.data)

        # Verify that the SiteConfig and Organizations
        # are created in the database
        self.assertTrue(
            SiteConfig.objects.filter(name="New Drought Map Hub").exists()
        )
        self.assertTrue(
            Organization.objects.filter(name="Organization 1").exists()
        )
        self.assertTrue(
            Organization.objects.filter(name="Organization 2").exists()
        )

    def test_setup_when_already_configured(self):
        """
        Test the setup endpoint when the application is already configured.
        """
        # First, perform a successful setup
        self.test_successful_setup()
        url = reverse("setup", kwargs={"version": "v1"})
        data = {
            "name": "Another Drought Map Hub",
            "geojson_file": self.geojson_file.open("rb"),
            "organizations": [
                {
                    "name": "Organization 3",
                    "logo": self.org_image_1.open("rb"),
                    "website": "https://www.organization3.com",
                    "is_twg": True,
                    "is_collaborator": False,
                }
            ],
        }
        response = self.client.post(
            url,
            data,
            format="multipart",
            HTTP_X_SETUP_SECRET="test-secret-key",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"],
            "Setup has already been completed. Cannot reconfigure."
        )
        # Close the opened files
        data["geojson_file"].close()
        data["organizations"][0]["logo"].close()

        # Verify that no additional SiteConfig or Organizations
        # are created in the database
        self.assertEqual(SiteConfig.objects.count(), 1)
        self.assertEqual(Organization.objects.count(), 2)

    def test_setup_with_missing_data(self):
        """
        Test the setup endpoint with missing required data.
        """
        url = reverse("setup", kwargs={"version": "v1"})
        data = {
            # "name" is missing
            "geojson_file": self.geojson_file.open("rb"),
            "organizations": [
                {
                    "name": "Organization 1",
                    "logo": self.org_image_1.open("rb"),
                    "website": "https://www.organization1.com",
                    "is_twg": True,
                    "is_collaborator": True,
                }
            ],
        }
        response = self.client.post(
            url,
            data,
            format="multipart",
            HTTP_X_SETUP_SECRET="test-secret-key",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Response should show error message for the missing name
        self.assertIn("name", response.data)
        self.assertEqual(
            response.data["name"][0],
            "This field is required."
        )

        # Close the opened files
        data["geojson_file"].close()
        data["organizations"][0]["logo"].close()

        # Verify that no SiteConfig or Organizations
        # are created in the database
        self.assertFalse(SiteConfig.objects.exists())
        self.assertFalse(Organization.objects.exists())

    def test_setup_with_invalid_file(self):
        """
        Test the setup endpoint with an invalid geojson file.
        """
        url = reverse("setup", kwargs={"version": "v1"})
        invalid_file = self.path / "static/invalid.txt"
        data = {
            "name": "New Drought Map Hub",
            "geojson_file": invalid_file.open("rb"),
            "organizations": [
                {
                    "name": "Organization 1",
                    "logo": self.org_image_1.open("rb"),
                    "website": "https://www.organization1.com",
                    "is_twg": True,
                    "is_collaborator": True,
                }
            ],
        }
        response = self.client.post(
            url,
            data,
            format="multipart",
            HTTP_X_SETUP_SECRET="test-secret-key",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Response should show error message for the invalid file
        self.assertIn("geojson_file", response.data)
        self.assertEqual(
            response.data["geojson_file"][0],
            "Invalid file format. Please upload a valid GeoJSON file."
        )
        # Close the opened files
        data["geojson_file"].close()
        data["organizations"][0]["logo"].close()
        # Note: invalid_file is a Path object, not a file handle

        # Verify that no SiteConfig or Organizations
        # are created in the database
        self.assertFalse(SiteConfig.objects.exists())
        self.assertFalse(Organization.objects.exists())

    def test_setup_with_no_organizations(self):
        """
        Test the setup endpoint with no organizations provided.
        """
        url = reverse("setup", kwargs={"version": "v1"})
        data = {
            "name": "New Drought Map Hub",
            "geojson_file": self.geojson_file.open("rb"),
            "organizations": [],
        }
        response = self.client.post(
            url,
            data,
            format="multipart",
            HTTP_X_SETUP_SECRET="test-secret-key",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("organizations", response.data)
        # Check if it's Django required field error or our custom validation
        if isinstance(response.data["organizations"], list):
            self.assertEqual(
                str(response.data["organizations"][0]),
                "This field is required."
            )
        else:
            self.assertEqual(
                str(response.data["organizations"]),
                "At least one organization is required."
            )
        # Close the opened files
        data["geojson_file"].close()

        # Verify that no SiteConfig or Organizations
        # are created in the database
        self.assertFalse(SiteConfig.objects.exists())
        self.assertFalse(Organization.objects.exists())

    def test_setup_with_invalid_organization_data(self):
        """
        Test the setup endpoint with invalid organization data.
        """
        url = reverse("setup", kwargs={"version": "v1"})
        data = {
            "name": "New Drought Map Hub",
            "geojson_file": self.geojson_file.open("rb"),
        }
        # Add organization with missing name (invalid data)
        data["organizations[0][website]"] = "https://www.organization1.com"
        # Missing: data["organizations[0][name]"]
        # Also skipping logo due to image format issues
        # data["organizations[0][logo]"] = self.org_image_1.open("rb")
        response = self.client.post(
            url,
            data,
            format="multipart",
            HTTP_X_SETUP_SECRET="test-secret-key"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Response should show error message for the missing name
        self.assertIn("organizations", response.data)
        # Check that the organizations field contains validation errors
        organizations_errors = response.data["organizations"]
        self.assertIsInstance(organizations_errors, list)
        self.assertTrue(len(organizations_errors) > 0)
        # Check that the first organization has a name error
        org_error = organizations_errors[0]
        self.assertIn("name", org_error)
        # The error could be either "required" or "null" depending on how
        # the data is parsed
        error_msg = str(org_error["name"][0])
        self.assertIn(
            error_msg,
            ["This field is required.", "This field may not be null."]
        )

        # Close the opened files
        data["geojson_file"].close()
        # data["organizations[0][logo]"].close()

        # Verify that no SiteConfig or Organizations
        # are created in the database
        self.assertFalse(SiteConfig.objects.exists())
        self.assertFalse(Organization.objects.exists())

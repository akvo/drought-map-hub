from rest_framework.test import APITestCase
from rest_framework import status
from django.test.utils import override_settings
from django.urls import reverse
from django.core.management import call_command
from api.v1.v1_setup.models import Organization
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser


@override_settings(USE_TZ=False, TEST_ENV=True)
class OrganizationAPITest(APITestCase):

    def setUp(self) -> None:
        """
        Set up the test environment.
        """
        self.url = reverse("organizations", kwargs={"version": "v1"})
        # Create sample Organization instances
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
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)

        self.admin = (
            SystemUser.objects.filter(
                role=UserRoleTypes.admin
            ).order_by("?").first()
        )
        self.client.force_authenticate(user=self.admin)

        return super().setUp()

    def test_get_organizations(self):
        """
        Test the organizations endpoint for retrieving organization list.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertIsInstance(response.data["results"], list)
        self.assertEqual(len(response.data["results"]), 2)
        org_names = [org["name"] for org in response.data["results"]]
        self.assertIn("Test Organization", org_names)
        self.assertIn("Another Organization", org_names)

    def test_get_twg_organizations(self):
        """
        Test retrieving only TWG organizations.
        """
        response = self.client.get(self.url, {"is_twg": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertIsInstance(response.data["results"], list)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["name"],
            "Test Organization"
        )

    def test_get_collaborator_organizations(self):
        """
        Test retrieving only collaborator organizations.
        """
        response = self.client.get(self.url, {"is_collaborator": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertIsInstance(response.data["results"], list)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["name"],
            "Another Organization"
        )

    def test_update_organization(self):
        """
        Test updating an organization.
        """
        org = Organization.objects.first()
        update_url = reverse(
            "organization-detail",
            kwargs={"version": "v1", "pk": org.id}
        )
        data = {
            "name": "Updated Organization",
            "website": "https://www.updatedorg.com",
            "is_twg": False,
            "is_collaborator": True
        }
        response = self.client.put(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        org.refresh_from_db()
        self.assertEqual(org.name, "Updated Organization")
        self.assertEqual(org.website, "https://www.updatedorg.com")
        self.assertFalse(org.is_twg)
        self.assertTrue(org.is_collaborator)

    def test_delete_organization(self):
        """
        Test deleting an organization.
        """
        org = Organization.objects.first()
        delete_url = reverse(
            "organization-detail",
            kwargs={"version": "v1", "pk": org.id}
        )
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Organization.objects.filter(id=org.id).exists())

    def test_get_nonexistent_organization(self):
        """
        Test retrieving a non-existent organization.
        """
        non_existent_id = 9999
        detail_url = reverse(
            "organization-detail",
            kwargs={"version": "v1", "pk": non_existent_id}
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "No Organization matches the given query."
        )

    def test_update_nonexistent_organization(self):
        """
        Test updating a non-existent organization.
        """
        non_existent_id = 9999
        update_url = reverse(
            "organization-detail",
            kwargs={"version": "v1", "pk": non_existent_id}
        )
        data = {
            "name": "Nonexistent Organization",
            "website": "https://www.nonexistentorg.com",
            "is_twg": False,
            "is_collaborator": True
        }
        response = self.client.put(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "No Organization matches the given query."
        )

    def test_delete_nonexistent_organization(self):
        """
        Test deleting a non-existent organization.
        """
        non_existent_id = 9999
        delete_url = reverse(
            "organization-detail",
            kwargs={"version": "v1", "pk": non_existent_id}
        )
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "No Organization matches the given query."
        )

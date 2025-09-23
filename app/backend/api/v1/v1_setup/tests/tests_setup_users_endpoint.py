from django.urls import reverse
from django.test.utils import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from api.v1.v1_setup.models import Organization
from api.v1.v1_users.models import SystemUser, UserRoleTypes


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    SETUP_SECRET_KEY="test-secret-key"
)
class SetupUsersAPITest(APITestCase):
    def setUp(self):
        self.url = reverse("user-setup", kwargs={"version": "v1"})
        # Seed the organization data with is_twg = True
        self.org_1 = Organization.objects.create(
            name="Org 1",
            website="https://org1.example.com",
            logo="org_1_logo.png",
            is_twg=True
        )
        self.org_2 = Organization.objects.create(
            name="Org 2",
            website="https://org2.example.com",
            logo="org_2_logo.png",
            is_collaborator=True
        )

        self.client.credentials(HTTP_X_SETUP_SECRET='test-secret-key')

    def test_successful_user_setup(self):
        """Test successful user setup."""
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "reviewers": [
                {
                    "email": "reviewer@org1.example.com",
                    "name": "Reviewer One",
                    "organization_id": self.org_1.id
                },
                {
                    "email": "reviewer@org2.example.com",
                    "name": "Reviewer Two",
                    "organization_id": self.org_2.id
                }
            ]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(
            list(data.keys()),
            ['name', 'email', 'reviewers']
        )
        # Verify admin user was created
        admin_user = SystemUser.objects.filter(
            email=payload["email"],
            role=UserRoleTypes.admin
        ).first()
        self.assertIsNotNone(admin_user, "Admin user should be created")
        self.assertEqual(admin_user.name, payload["name"])
        # Verify reviewers were created
        for reviewer_data in payload["reviewers"]:
            reviewer = SystemUser.objects.filter(
                email=reviewer_data["email"],
                role=UserRoleTypes.reviewer
            ).first()
            self.assertIsNotNone(
                reviewer,
                f"Reviewer {reviewer_data['email']} should be created"
            )
            self.assertEqual(reviewer.name, reviewer_data["name"])
            self.assertEqual(
                reviewer.organization_id,
                reviewer_data["organization_id"]
            )

    def test_user_setup_without_authentication(self):
        """Test user setup without proper authentication header."""
        self.client.credentials()  # Remove authentication
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "reviewers": []
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {"detail": "Forbidden."})

    def test_user_setup_with_invalid_authentication(self):
        """Test user setup with invalid authentication header."""
        self.client.credentials(HTTP_X_SETUP_SECRET='wrong-secret')
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "reviewers": []
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {"detail": "Forbidden."})

    def test_user_setup_missing_required_fields(self):
        """Test user setup with missing required fields."""
        payload = {
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.json())

    def test_user_setup_invalid_email(self):
        """Test user setup with invalid email format."""
        payload = {
            "name": "testuser",
            "email": "invalid-email",
            "password": "testpass123",
            "confirm_password": "testpass123"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.json())

    def test_user_setup_password_too_short(self):
        """Test user setup with password too short."""
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "123",
            "confirm_password": "123"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.json())

    def test_user_setup_password_mismatch(self):
        """Test user setup with password confirmation mismatch."""
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "different123"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.json())

    def test_user_setup_without_reviewers(self):
        """Test user setup without reviewers (should still work)."""
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify admin user was created
        admin_user = SystemUser.objects.filter(
            email=payload["email"],
            role=UserRoleTypes.admin
        ).first()
        self.assertIsNotNone(admin_user)

    def test_user_setup_with_empty_reviewers_list(self):
        """Test user setup with empty reviewers list."""
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "reviewers": []
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify admin user was created
        admin_user = SystemUser.objects.filter(
            email=payload["email"],
            role=UserRoleTypes.admin
        ).first()
        self.assertIsNotNone(admin_user)

    def test_user_setup_reviewer_missing_required_fields(self):
        """Test user setup with reviewer missing required fields."""
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "reviewers": [
                {
                    "email": "reviewer@org1.example.com",
                    # Missing name and organization_id
                }
            ]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reviewers', response.json())

    def test_user_setup_reviewer_invalid_organization(self):
        """Test user setup with reviewer having invalid organization ID."""
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "reviewers": [
                {
                    "email": "reviewer@org1.example.com",
                    "name": "Reviewer One",
                    "organization_id": 99999  # Non-existent organization
                }
            ]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reviewers', response.json())

    def test_user_setup_duplicate_admin_email(self):
        """Test user setup with duplicate admin email."""
        # Create an existing user with same email
        SystemUser.objects._create_user(
            name="Existing User",
            email="testuser@example.com",
            password="password123"
        )

        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_setup_duplicate_reviewer_email(self):
        """Test user setup with duplicate reviewer email."""
        # Create an existing user with same email as reviewer
        SystemUser.objects._create_user(
            name="Existing Reviewer",
            email="reviewer@org1.example.com",
            password="password123"
        )
        payload = {
            "name": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
            "reviewers": [
                {
                    "email": "reviewer@org1.example.com",
                    "name": "Reviewer One",
                    "organization_id": self.org_1.id
                }
            ]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_setup_status(self):
        """Test GET endpoint to check setup status."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('is_configured', data)
        self.assertIsInstance(data['is_configured'], bool)

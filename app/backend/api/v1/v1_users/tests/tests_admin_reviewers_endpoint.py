from django.urls import reverse
from django.core.management import call_command
from django.db.models import Q
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_users.serializers import UserReviewerSerializer


class ReviewerListAPITestCase(APITestCase):
    def setUp(self):
        call_command("fake_users_seeder", "--test", True, "--repeat", 3)

        # Create an admin user
        self.admin_user = SystemUser.objects.create_superuser(
            name="Admin",
            email="admin@example.com",
            password="adminpassword"
        )

        # Create a reviewer user without technical working group
        self.reviewer_user = SystemUser.objects._create_user(
            name="John Doe",
            email="john.doe@example.com",
            password="userpassword",
        )

        # Set some test data
        self.test_data = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).order_by("name").all()

        # Set up the API client
        self.client = APIClient()
        self.url = reverse(
            "reviewer-list",
            kwargs={"version": "v1"}
        )

    def test_authenticated_admin_can_access(self):
        # Force authentication as the admin user
        self.client.force_authenticate(user=self.admin_user)

        # Send GET request
        response = self.client.get(self.url)

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert response structure
        expected_data = {
            "current": 1,  # Assuming the default pagination starts at page 1
            "total": len(self.test_data),
            "total_page": 1,  # Assuming all items fit on one page
            "data": UserReviewerSerializer(self.test_data, many=True).data,
        }
        self.assertEqual(response.data, expected_data)

    def test_unauthenticated_user_cannot_access(self):
        # Ensure the client is not authenticated
        self.client.force_authenticate(user=None)

        # Send GET request
        response = self.client.get(self.url)

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_user_cannot_access(self):
        # Force authentication as a reviewer user
        self.client.force_authenticate(user=self.reviewer_user)

        # Send GET request
        response = self.client.get(self.url)

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_search_reviewers_by_name(self):
        # Force authentication as the admin user
        self.client.force_authenticate(user=self.admin_user)

        # Send GET request
        reviewer = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).order_by("?").first()
        search = reviewer.name[:3]
        url = f"{self.url}?search={search}"
        response = self.client.get(url)

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        total = SystemUser.objects.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search)
        ).count()
        self.assertEqual(response.data["total"], total)

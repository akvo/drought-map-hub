from rest_framework.test import APITestCase
from rest_framework import status
from django.core.management import call_command
from django.urls import reverse
from api.v1.v1_users.models import SystemUser, UserRoleTypes


class AdminContactsAPITestCase(APITestCase):
    def setUp(self):
        call_command("generate_admin_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)

        self.user = (
            SystemUser.objects.filter(
                role=UserRoleTypes.admin
            ).order_by("?").first()
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse(
            "admin_contacts",
            kwargs={"version": "v1"}
        )

    def test_get_contacts_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        admins = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).all()
        contacts = [
            a.email
            for a in admins
        ]
        self.assertEqual(response.data, {
            "contacts": contacts
        })

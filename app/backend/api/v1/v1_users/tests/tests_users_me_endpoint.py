from django.test import TestCase
from django.core.management import call_command
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.tests.mixins import ProfileTestHelperMixin
from api.v1.v1_users.constants import UserRoleTypes


class MyProfileTestCase(TestCase, ProfileTestHelperMixin):
    def setUp(self):
        call_command(
            "generate_admin_seeder", "--test", True
        )
        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.token = self.get_auth_token(
            email=self.user.email,
            password="Changeme123"
        )

    def test_successfully_get_my_account(self):
        req = self.client.get(
            "/api/v1/users/me",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )
        self.assertTrue(req.status_code, 200)
        res = req.json()
        self.assertEqual(
            list(res),
            [
                "id",
                "name",
                "email",
                "role",
                "email_verified",
                "abilities",
                "technical_working_group",
            ]
        )
        self.assertFalse(res["email_verified"])
        self.assertEqual(res["email"], self.user.email)

    def test_my_deleted_account(self):
        self.user.soft_delete()
        req = self.client.get(
            "/api/v1/users/me",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )
        self.assertTrue(req.status_code, 401)
        res = req.json()
        self.assertEqual(
            res,
            {"detail": "User not found", "code": "user_not_found"}
        )

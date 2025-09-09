import uuid
from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes


@override_settings(USE_TZ=False, TEST_ENV=True)
class UsersResetPasswordTestCase(TestCase):
    def setUp(self):
        call_command(
            "generate_admin_seeder", "--test", True
        )
        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()

    def test_successfully_reset_password(self):
        payload = {"email": self.user.email}
        self.assertFalse(self.user.reset_password_code)
        req = self.client.post(
            "/api/v1/auth/forgot-password",
            payload,
            content_type="application/json",
        )
        self.assertEqual(req.status_code, 200)
        user = SystemUser.objects.first()
        password_code = user.reset_password_code
        self.assertTrue(password_code)
        new_password = "Testing1234"
        payload = {"password": new_password, "confirm_password": new_password}
        req = self.client.post(
            f"/api/v1/auth/reset-password?code={password_code}",
            payload,
            content_type="application/json",
        )
        self.assertEqual(
            req.json(),
            {"message": "Password reset successfully"}
        )
        self.assertEqual(req.status_code, 200)
        # reset password code should be cleared after successful reset
        self.assertFalse(self.user.reset_password_code)
        payload = {"email": self.user.email, "password": new_password}
        req = self.client.post(
            "/api/v1/auth/login", payload, content_type="application/json"
        )
        self.assertEqual(req.status_code, 200)

    def test_invalid_code(self):
        passcode = str(uuid.uuid4())
        payload = {
            "password": "Testing1234",
            "confirm_password": "Testing1234",
        }
        req = self.client.post(
            f"/api/v1/auth/reset-password?code={passcode}",
            payload,
            content_type="application/json",
        )
        self.assertEqual(req.json(), {"message": "Invalid code"})
        self.assertEqual(req.status_code, 400)

    def test_invalid_confirm_password(self):
        passcode = str(uuid.uuid4())
        payload = {
            "password": "Testing1234",
            "confirm_password": "Testing-1234",
        }
        req = self.client.post(
            f"/api/v1/auth/reset-password?code={passcode}",
            payload,
            content_type="application/json",
        )
        self.assertEqual(
            req.json(),
            {"message": "Confirm password and password are not same"},
        )
        self.assertEqual(req.status_code, 400)

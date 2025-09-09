from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes


@override_settings(USE_TZ=False, TEST_ENV=True)
class VerifyPasswordCodeTestCase(TestCase):
    def setUp(self):
        call_command(
            "generate_admin_seeder", "--test", True
        )
        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()

    def test_verify_password_code(self):
        self.assertFalse(self.user.reset_password_code)
        self.assertFalse(self.user.reset_password_code_expiry)
        self.user.generate_reset_password_code()
        self.assertTrue(self.user.reset_password_code)
        self.assertTrue(
            self.user.reset_password_code_expiry > timezone.now()
        )
        code = self.user.reset_password_code
        req = self.client.get(
            f"/api/v1/auth/verify-password-code?code={code}",
            content_type="application/json",
        )
        self.assertEqual(req.status_code, 200)
        res = req.json()
        self.assertEqual(res, {"message": "OK"})

    def test_verify_password_code_invalid_code(self):
        payload = {"code": "invalid-code"}
        req = self.client.get(
            "/api/v1/auth/verify-password-code",
            payload,
            content_type="application/json",
        )
        self.assertEqual(req.status_code, 400)

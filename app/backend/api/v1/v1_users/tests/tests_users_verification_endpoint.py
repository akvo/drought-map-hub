from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from django.conf import settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes


@override_settings(USE_TZ=False, WEBDOMAIN="http://example.com")
class VerificationTestCase(TestCase):
    def setUp(self):
        call_command(
            "generate_admin_seeder", "--test", True
        )
        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()

    def test_successfully_verified(self):
        req = self.client.get(
            f"/api/v1/email/verify?code={self.user.email_verification_code}",
            content_type="application/json",
        )
        self.assertEqual(req.status_code, 302)

        # Assert that the redirect URL is correct
        expected_url = f"{settings.WEBDOMAIN}/login?verified=true"
        self.assertEqual(req["Location"], expected_url)

        current_user = SystemUser.objects.first()
        self.assertTrue(current_user.email_verified)
        self.assertIsNone(current_user.email_verification_expiry)

    def test_invalid_code(self):
        req = self.client.get(
            "/api/v1/email/verify?code=INVALID",
            content_type="application/json"
        )
        self.assertEqual(req.status_code, 400)
        res = req.json()
        self.assertEqual(res, {"message": "“INVALID” is not a valid UUID."})

    def test_user_email_verified(self):
        self.user.email_verified = True
        self.user.save()

        req = self.client.get(
            f"/api/v1/email/verify?code={self.user.email_verification_code}",
            content_type="application/json",
        )
        self.assertEqual(req.status_code, 302)

        expected_url = f"{settings.WEBDOMAIN}/login"
        self.assertEqual(req["Location"], expected_url)

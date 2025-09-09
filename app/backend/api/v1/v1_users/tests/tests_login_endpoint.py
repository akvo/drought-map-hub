from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes


@override_settings(USE_TZ=False, TEST_ENV=True)
class LoginTestCase(TestCase):
    def setUp(self):
        call_command(
            "generate_admin_seeder", "--test", True
        )
        call_command(
            "generate_roles_n_abilities_seeder", "--test", True
        )
        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.default_password = "Changeme123"

    def test_successfully_logged_in(self):
        payload = {
            "email": self.user.email,
            "password": self.default_password
        }
        req = self.client.post(
            "/api/v1/auth/login",
            payload,
            content_type="application/json"
        )
        self.assertEqual(req.status_code, 200)
        res = req.json()
        self.assertEqual(
            list(res),
            ["user", "token", "expiration_time"]
        )
        self.assertEqual(
            list(res["user"]),
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
        self.assertEqual(len(res["user"]["abilities"]), 1)

    def test_all_inputs_are_required(self):
        payload = {
            "email": "",
            "password": ""
        }
        req = self.client.post(
            "/api/v1/auth/login",
            payload,
            content_type="application/json"
        )
        self.assertEqual(req.status_code, 400)
        res = req.json()
        self.assertEqual(
            res,
            {"message": "email may not be blank.|password may not be blank."}
        )

    def test_invalid_input_email(self):
        payload = {
            "email": "john",
            "password": self.default_password
        }
        req = self.client.post(
            "/api/v1/auth/login",
            payload,
            content_type="application/json"
        )
        self.assertEqual(req.status_code, 400)
        res = req.json()
        self.assertEqual(
            res,
            {"message": "Enter a valid email address."}
        )

    def test_invalid_login_credentials(self):
        payload = {
            "email": "john@test.com",
            "password": "OPen1234"
        }
        req = self.client.post(
            "/api/v1/auth/login",
            payload,
            content_type="application/json"
        )
        self.assertEqual(req.status_code, 401)
        res = req.json()
        self.assertEqual(
            res,
            {"message": "Invalid login credentials"}
        )

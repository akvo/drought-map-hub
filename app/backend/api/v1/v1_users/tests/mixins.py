import typing
from django.core.management.color import no_style
from django.db import connection
from django.test.client import Client


class HasTestClientProtocol(typing.Protocol):
    @property
    def client(self) -> Client: ...  # pragma: no cover


class ProfileTestHelperMixin:

    @staticmethod
    def reset_db_sequence(*models):
        """
        Auto fields are no longer incrementing after running create with
        explicit id parameter

        see: https://code.djangoproject.com/ticket/11423
        """
        sequence_sql = connection.ops.sequence_reset_sql(no_style(), models)
        with connection.cursor() as cursor:
            for sql in sequence_sql:
                cursor.execute(sql)

    def get_auth_token(
        self: HasTestClientProtocol,
        email: str,
        password: str
    ) -> str:
        payload = {"email": email, "password": password}
        response = self.client.post(
            "/api/v1/auth/login", payload, content_type="application/json"
        )
        user = response.json()
        return user.get("token")

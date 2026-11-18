from django.contrib.auth.base_user import BaseUserManager
from django.db.models import CharField, Value
from django.db.models.functions import Cast, Concat
from utils.soft_deletes_model import SoftDeletesManager, SoftDeletesQuerySet
from uuid import uuid4
from api.v1.v1_users.constants import UserRoleTypes


class UserManager(BaseUserManager, SoftDeletesManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.

        If a soft-deleted account already uses this email, rename that stale
        row's email to free it, then create a fresh account. Reviving the old
        row would carry over every field not in ``extra_fields``
        (``is_superuser``, ``email_verified``, groups/permissions); deleting
        it would cascade to that user's reviews.
        (Active duplicates are rejected earlier by serializer validation;
        ``reset_setup --with-users`` covers the dev re-run case.)
        """
        if not email:
            raise ValueError("The given email must be set")
        (
            SoftDeletesQuerySet(self.model)
            .only_deleted()
            .filter(email=email)
            .update(
                email=Concat(
                    Value("deleted-"),
                    Cast("id", CharField()),
                    Value("-"),
                    "email",
                    output_field=CharField(),
                )
            )
        )
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.email_verification_code = uuid4()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRoleTypes.admin)

        if extra_fields.get("role") is not UserRoleTypes.admin:
            raise ValueError("Invalid Admin role")

        return self._create_user(email, password, **extra_fields)

import uuid
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core import signing
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

from utils.soft_deletes_model import SoftDeletes
from utils.custom_manager import UserManager
from api.v1.v1_users.constants import (
    UserRoleTypes,
    TechnicalWorkingGroup,
    ActionEnum,
)


class SystemUser(AbstractBaseUser, PermissionsMixin, SoftDeletes):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    role = models.IntegerField(
        choices=UserRoleTypes.FieldStr.items(),
        default=UserRoleTypes.reviewer,
    )
    email_verified = models.BooleanField(default=False)
    email_verification_code = models.UUIDField(default=None, null=True)
    email_verification_expiry = models.DateTimeField(
        null=True,
        blank=True
    )
    reset_password_code = models.UUIDField(default=None, null=True, blank=True)
    reset_password_code_expiry = models.DateTimeField(null=True, blank=True)
    # Add Technical working group field from Enum class
    technical_working_group = models.IntegerField(
        choices=TechnicalWorkingGroup.FieldStr.items(),
        default=None,
        null=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "role"]

    def delete(self, using=None, keep_parents=False, hard: bool = False):
        if hard:
            return super().delete(using, keep_parents)
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def soft_delete(self) -> None:
        self.delete(hard=False)

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    def get_sign_pk(self):
        return signing.dumps(self.pk)

    def generate_reset_password_code(self):
        self.reset_password_code = uuid.uuid4()
        self.reset_password_code_expiry = timezone.now() + timedelta(hours=1)
        self.save(
            update_fields=["reset_password_code", "reset_password_code_expiry"]
        )
        return self.reset_password_code

    def is_reset_code_valid(self):
        if self.reset_password_code and self.reset_password_code_expiry:
            return timezone.now() < self.reset_password_code_expiry
        return False

    @property
    def is_staff(self):
        return self.is_superuser

    class Meta:
        db_table = "system_user"


class Ability(models.Model):
    role = models.IntegerField(
        choices=UserRoleTypes.FieldStr.items(),
        default=UserRoleTypes.reviewer,
    )
    action = models.CharField(
        max_length=10,
        choices=ActionEnum.choices(),
    )
    subject = models.CharField(max_length=50)  # e.g., "Publication", "Review"
    conditions = models.JSONField(blank=True, null=True)  # Optional conditions

    class Meta:
        db_table = "ability"
        unique_together = ('role', 'action', 'subject')

    def __str__(self):
        return f"{self.role}: {self.action} {self.subject}"

    def clean(self):
        # Validate that the action is one of the valid choices
        valid_actions = [action.value for action in ActionEnum]
        if self.action not in valid_actions:  # pragma: no cover
            raise ValidationError({  # pragma: no cover
                "action": f"'{self.action}' is not a valid action."
            })

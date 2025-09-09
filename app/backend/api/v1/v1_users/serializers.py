import re
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from api.v1.v1_users.models import (
    SystemUser,
    Ability,
)
from utils.custom_serializer_fields import (
    CustomCharField,
    CustomEmailField,
)
from .constants import TechnicalWorkingGroup


class AbilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ability
        fields = ['action', 'subject', 'conditions']


class LoginSerializer(serializers.Serializer):
    email = CustomEmailField()
    password = CustomCharField()


class UserSerializer(serializers.ModelSerializer):
    abilities = serializers.SerializerMethodField()

    @extend_schema_field(AbilitySerializer(many=True))
    def get_abilities(self, instance):
        _abilities = Ability.objects.filter(
            role=instance.role
        ).all()
        return AbilitySerializer(_abilities, many=True).data

    class Meta:
        model = SystemUser
        fields = [
            "id",
            "name",
            "email",
            "role",
            "email_verified",
            "abilities",
            "technical_working_group",
        ]


class VerifyEmailSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        if not SystemUser.objects.filter(
            email_verification_code=value
        ).exists():
            raise serializers.ValidationError(  # pragma: no cover
                "Invalid code"
            )
        return value


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = CustomEmailField()

    def validate_email(self, value):
        current_user = self.context.get("user")
        if current_user.email != value:
            raise serializers.ValidationError("Email address not found.")
        if current_user.email_verified:
            raise serializers.ValidationError("Email is already verified.")
        return value


class UpdateUserSerializer(serializers.ModelSerializer):
    name = CustomCharField(
        required=False,
        allow_null=True,
    )
    email = CustomEmailField(
        required=False,
        allow_null=True,
    )
    technical_working_group = serializers.ChoiceField(
        choices=[
            (key, value)
            for key, value in TechnicalWorkingGroup.FieldStr.items()
        ],
        required=False,
    )

    class Meta:
        model = SystemUser
        fields = [
            "name",
            "email",
            "technical_working_group",
        ]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance


class ForgotPasswordSerializer(serializers.Serializer):
    email = CustomEmailField()

    def validate_email(self, value):
        if not SystemUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "User with this email does not exist."
            )
        return value


class ResetPasswordSerializer(serializers.Serializer):
    password = CustomCharField()
    confirm_password = CustomCharField()

    def validate_confirm_password(self, value):
        password = self.initial_data.get("password")
        if password != value:
            raise serializers.ValidationError(
                "Confirm password and password are not same"
            )
        return value

    def validate_password(self, value):
        criteria = re.compile(
            r"^(?=.*[a-z])(?=.*\d)(?=.*[A-Z])(?=.*^\S*$)(?=.{8,})"
        )
        if not criteria.match(value):
            raise serializers.ValidationError(  # pragma: no cover
                "False Password Criteria"
            )
        return value


class VerifyPasswordTokenSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        if not SystemUser.objects.filter(reset_password_code=value).exists():
            raise serializers.ValidationError("Invalid code")
        return value


class UserReviewerSerializer(serializers.ModelSerializer):
    technical_working_group = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_technical_working_group(self, obj):
        if not obj.technical_working_group:
            return None
        return TechnicalWorkingGroup.FieldStr[obj.technical_working_group]

    class Meta:
        model = SystemUser
        fields = [
            "id",
            "name",
            "email",
            "email_verified",
            "technical_working_group",
        ]

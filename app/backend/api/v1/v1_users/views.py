from datetime import datetime, timedelta
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import status, serializers
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import authenticate
from django.http import HttpResponseRedirect
from django.conf import settings
from django.db.models import Q
from django_q.tasks import async_task
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from api.v1.v1_users.serializers import (
    LoginSerializer,
    UserSerializer,
    UpdateUserSerializer,
    VerifyEmailSerializer,
    ResendVerificationEmailSerializer,
    ForgotPasswordSerializer,
    VerifyPasswordTokenSerializer,
    ResetPasswordSerializer,
    UserReviewerSerializer,
)
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from utils.custom_serializer_fields import validate_serializers_message
from utils.default_serializers import DefaultResponseSerializer
from uuid import uuid4
from api.v1.v1_jobs.models import Jobs, JobTypes, JobStatus
from utils.custom_permissions import IsAdmin
from utils.custom_pagination import Pagination


@extend_schema(
    request=LoginSerializer,
    responses={200: UserSerializer, 401: DefaultResponseSerializer},
    tags=["Auth"],
)
@api_view(["POST"])
def login(request, version):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
    )

    if user:
        user.last_login = timezone.now()
        user.save()
        refresh = RefreshToken.for_user(user)
        # Get the expiration time of the new token
        expiration_time = datetime.fromtimestamp(refresh.access_token["exp"])
        expiration_time = timezone.make_aware(expiration_time)

        data = {}
        data["user"] = UserSerializer(instance=user).data
        data["token"] = str(refresh.access_token)
        data["expiration_time"] = expiration_time
        response = Response(
            data,
            status=status.HTTP_200_OK,
        )
        response.set_cookie(
            "AUTH_TOKEN", str(refresh.access_token), expires=expiration_time
        )
        return response
    return Response(
        {"message": "Invalid login credentials"},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@extend_schema(
    responses={200: DefaultResponseSerializer},
    tags=["Users"],
    parameters=[
        OpenApiParameter(
            name="code",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
    summary="Verify the user's email using the verification link.",
)
@api_view(["GET"])
def verify_email(request, version):
    serializer = VerifyEmailSerializer(data=request.GET)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    code = serializer.validated_data.get("code")
    user = SystemUser.objects.get(email_verification_code=code)
    if user.email_verified:
        return HttpResponseRedirect(f"{settings.WEBDOMAIN}/login")
    user.email_verified = True
    user.updated = timezone.now()
    user.email_verification_expiry = None
    user.save()
    return HttpResponseRedirect(f"{settings.WEBDOMAIN}/login?verified=true")


@extend_schema(
    request=ResendVerificationEmailSerializer,
    responses={200: DefaultResponseSerializer},
    tags=["Users"],
    summary="Allows the user to request a new verification email.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_verification_email(request, version):
    serializer = ResendVerificationEmailSerializer(
        data=request.data,
        context={
            "user": request.user
        }
    )
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = request.user
    # Response 400 when email_verification_expiry less than 1 hour
    code_expiry = user.email_verification_expiry
    if (
        code_expiry and
        code_expiry > timezone.now()
    ):
        return Response(
            {
                "message": (
                    "Verification email already sent. "
                    "Please wait before requesting a new one."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    code_expiry = timezone.now() + timedelta(hours=1)
    user.email_verification_code = uuid4()
    user.email_verification_expiry = code_expiry
    user.save()
    job = Jobs.objects.create(
        type=JobTypes.verification_email,
        status=JobStatus.on_progress,
        result=serializer.validated_data["email"],
    )
    task_id = async_task(
        "api.v1.v1_jobs.job.notify_verification_email",
        serializer.validated_data["email"],
        user.email_verification_code,
        hook="api.v1.v1_jobs.job.email_notification_results",
    )
    job.task_id = task_id
    job.save()
    return Response(
        {"message": "Verification email sent successfully"},
        status=status.HTTP_200_OK,
    )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        tags=["Users"],
        summary="Get user profile",
    )
    def get(self, request, version):
        return Response(
            UserSerializer(instance=request.user).data,
            status=status.HTTP_200_OK
        )

    @extend_schema(
        request=UpdateUserSerializer,
        responses={200: UserSerializer, 400: DefaultResponseSerializer},
        tags=["Users"],
        summary="Update user profile",
    )
    def put(self, request, version):
        serializer = UpdateUserSerializer(
            instance=request.user,
            data=request.data
        )
        if not serializer.is_valid():
            return Response(  # pragma: no cover
                {"message": validate_serializers_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            serializer.validated_data.get("email") and
            serializer.validated_data["email"] != request.user.email
        ):
            request.user.email_verified = False
            request.user.email_verification_code = uuid4()
            request.user.save()

            # Dispatch verification email job
            job = Jobs.objects.create(
                type=JobTypes.verification_email,
                status=JobStatus.on_progress,
                result=serializer.validated_data["email"],
            )
            task_id = async_task(
                "api.v1.v1_jobs.job.notify_verification_email",
                serializer.validated_data["email"],
                request.user.email_verification_code,
                hook="api.v1.v1_jobs.job.email_notification_results",
            )
            job.task_id = task_id
            job.save()
        user = serializer.save()
        return Response(
            UserSerializer(instance=user).data,
            status=status.HTTP_200_OK
        )


@extend_schema(
    request=ForgotPasswordSerializer,
    responses={200: ForgotPasswordSerializer},
    tags=["Auth"],
    summary="Forgot password",
)
@api_view(["POST"])
def forgot_password(request, version):
    serializer = ForgotPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"message": "OK"},
            status=status.HTTP_200_OK,
        )
    email = serializer.validated_data["email"]
    user = SystemUser.objects.get(email=email)
    user.generate_reset_password_code()

    # Dispatch forgot password job
    job = Jobs.objects.create(
        type=JobTypes.forgot_password,
        status=JobStatus.on_progress,
        result=serializer.validated_data["email"],
    )
    task_id = async_task(
        "api.v1.v1_jobs.job.notify_reset_password",
        user,
        hook="api.v1.v1_jobs.job.email_notification_results",
    )
    job.task_id = task_id
    job.save()
    return Response(
        {"message": "OK"},
        status=status.HTTP_200_OK,
    )


@extend_schema(
    responses={200: DefaultResponseSerializer},
    tags=["Auth"],
    summary="Verify password code",
    parameters=[
        OpenApiParameter(
            name="code",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
@api_view(["GET"])
def verify_password_code(request, version):
    serializer = VerifyPasswordTokenSerializer(data=request.GET)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    code = serializer.validated_data.get("code")
    user = SystemUser.objects.get(reset_password_code=code)
    if not user.is_reset_code_valid():
        return Response(  # pragma: no cover
            {"message": "Invalid code"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {"message": "OK"},
        status=status.HTTP_200_OK,
    )


@extend_schema(
    request=ResetPasswordSerializer,
    responses={200: DefaultResponseSerializer},
    tags=["Auth"],
    summary="Reset password",
    parameters=[
        OpenApiParameter(
            name="code",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
@api_view(["POST"])
def reset_password(request, version):
    new_password = ResetPasswordSerializer(data=request.data)
    if not new_password.is_valid():
        return Response(
            {"message": validate_serializers_message(new_password.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = VerifyPasswordTokenSerializer(data=request.GET)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    code = serializer.validated_data.get("code")
    user = SystemUser.objects.get(reset_password_code=code)
    if not user.is_reset_code_valid():
        return Response(  # pragma: no cover
            {"message": "Invalid code"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user.set_password(new_password.validated_data["password"])
    user.reset_password_code = None
    user.reset_password_code_expiry = None
    user.save()
    return Response(
        {"message": "Password reset successfully"},
        status=status.HTTP_200_OK,
    )


class ReviewerListAPI(GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserReviewerSerializer
    pagination_class = Pagination
    queryset = SystemUser.objects.filter(
        role=UserRoleTypes.reviewer,
        # email_verified=True
    ).order_by("name").all()

    @extend_schema(
        summary="Get all reviewers",
        description=(
            "Fetch all reviewers to start new publication"
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                default=1,
                required=True,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="search",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        tags=["Admin"],
        responses={
            200: UserReviewerSerializer(many=True),
            (200, "application/json"): inline_serializer(
                "ReviewerListResponse",
                fields={
                    "current": serializers.IntegerField(),
                    "total": serializers.IntegerField(),
                    "total_page": serializers.IntegerField(),
                    "data": UserReviewerSerializer(many=True),
                },
            ),
            400: DefaultResponseSerializer,
            500: DefaultResponseSerializer,
        },
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        search = request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search)
            )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

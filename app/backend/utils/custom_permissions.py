import hmac
from django.conf import settings
from rest_framework.permissions import BasePermission
from api.v1.v1_users.constants import UserRoleTypes


class IsReviewer(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == UserRoleTypes.reviewer:
            return True
        return False


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == UserRoleTypes.admin:
            return True
        return False


class HasApiKey(BasePermission):
    """Authenticates machine-to-machine pipeline push endpoints (DIH-1).

    Reads the raw key from the request META header defined by
    X_API_KEY_HEADER (default: HTTP_X_API_KEY) and compares it to
    settings.X_API_KEY using a constant-time comparison. No SystemUser /
    JWT involved — these endpoints are key-only. Per-tenant keys = MT-8.
    """

    def has_permission(self, request, view):
        sent = request.META.get(settings.X_API_KEY_HEADER, "")
        if not sent or not settings.X_API_KEY:
            return False
        return hmac.compare_digest(sent, settings.X_API_KEY)

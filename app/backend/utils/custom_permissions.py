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

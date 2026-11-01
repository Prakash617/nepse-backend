"""Permissions for technical analysis endpoints."""

from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Allows read access to all users, but restricts write/execute actions to staff."""

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)

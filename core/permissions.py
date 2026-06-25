from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsServiceAdvisor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "admin",
            "service_advisor",
        )


class IsMechanic(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "mechanic"


class IsCashier(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "admin",
            "cashier",
        )


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "POST"):
            return request.user.role in ("admin", "service_advisor")
        return request.user.role == "admin"


class IsAdminStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user.is_authenticated
        return request.user.role == "admin"

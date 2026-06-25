from rest_framework.permissions import BasePermission


class IsMechanicForAssignedJob(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "mechanic":
            return obj.assigned_mechanic == request.user
        return True

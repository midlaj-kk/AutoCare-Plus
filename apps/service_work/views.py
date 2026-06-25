from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ServiceWork
from .serializers import ServiceWorkSerializer, ServiceWorkStatusSerializer
from core.permissions import IsAdmin, IsMechanic, IsAdminStaffOrReadOnly
from apps.service_jobs.permissions import IsMechanicForAssignedJob
from .services import create_service_work, update_service_work


class ServiceWorkViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceWorkSerializer
    permission_classes = [IsAdminStaffOrReadOnly]
    queryset = ServiceWork.objects.none()

    def get_queryset(self):
        qs = ServiceWork.objects.select_related("service_job")
        if self.request.user.role == "mechanic":
            return qs.filter(service_job__assigned_mechanic=self.request.user)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsMechanic(), IsMechanicForAssignedJob()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        work = self.get_object()
        serializer = ServiceWorkStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_service_work(work, {"status": serializer.validated_data["status"]})
        return Response({"success": True, "message": "Work status updated."})

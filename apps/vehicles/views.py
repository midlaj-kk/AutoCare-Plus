from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Vehicle
from .serializers import VehicleSerializer
from core.permissions import IsAdmin, IsServiceAdvisor
from .services import create_vehicle, update_vehicle, delete_vehicle


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.filter(status="active")
    serializer_class = VehicleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["customer"]
    search_fields = ["vehicle_number"]
    ordering_fields = ["vehicle_number", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        return [IsServiceAdvisor()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        result, _ = delete_vehicle(instance)
        return Response(
            {"success": True, "message": f"Vehicle {result}."},
            status=status.HTTP_200_OK,
        )

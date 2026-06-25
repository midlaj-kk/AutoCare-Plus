from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Customer
from .serializers import CustomerSerializer
from core.permissions import IsAdmin, IsServiceAdvisor
from .services import create_customer, update_customer, delete_customer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(status="active")
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "phone"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        return [IsServiceAdvisor()]

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        result, _ = delete_customer(instance)
        return Response(
            {"success": True, "message": f"Customer {result}."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def vehicles(self, request, pk=None):
        customer = self.get_object()
        vehicles = customer.vehicles.filter(status="active")
        from apps.vehicles.serializers import VehicleListSerializer
        serializer = VehicleListSerializer(vehicles, many=True)
        return Response({"success": True, "data": serializer.data})

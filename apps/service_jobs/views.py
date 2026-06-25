from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import ServiceJob
from .serializers import (
    ServiceJobSerializer, ServiceJobCreateSerializer,
    ServiceJobStatusSerializer, AssignMechanicSerializer,
)
from core.permissions import IsAdmin, IsServiceAdvisor
from .services import (
    create_service_job, transition_job_status,
    assign_mechanic, change_mechanic,
)
from .selectors import get_service_jobs, get_job_by_id


class ServiceJobViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceJobSerializer
    queryset = ServiceJob.objects.none()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "assigned_mechanic"]
    search_fields = ["job_number", "vehicle__vehicle_number", "complaint"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return ServiceJobCreateSerializer
        return ServiceJobSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        if self.action in ("create", "assign_mechanic", "change_mechanic", "partial_update", "update"):
            return [IsServiceAdvisor()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = ServiceJob.objects.select_related("vehicle", "vehicle__customer", "assigned_mechanic")
        if user.role == "mechanic":
            return qs.filter(assigned_mechanic=user)
        return qs

    def perform_create(self, serializer):
        job = create_service_job(serializer.validated_data, self.request.user)
        return job

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_service_job(serializer.validated_data, request.user)
        output = ServiceJobSerializer(job, context={"request": request})
        return Response(
            {"success": True, "message": "Service job created.", "data": output.data},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        job = get_job_by_id(kwargs["pk"])
        if not job:
            return Response(
                {"success": False, "message": "Service job not found."},
                status=404,
            )
        serializer = ServiceJobSerializer(job, context={"request": request})
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["patch"])
    def assign_mechanic(self, request, pk=None):
        job = self.get_object()
        serializer = AssignMechanicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assign_mechanic(job, serializer.validated_data["mechanic_id"])
        return Response({"success": True, "message": "Mechanic assigned."})

    @action(detail=True, methods=["patch"])
    def change_mechanic(self, request, pk=None):
        job = self.get_object()
        serializer = AssignMechanicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_mechanic(job, serializer.validated_data["mechanic_id"])
        return Response({"success": True, "message": "Mechanic changed."})

    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        job = self.get_object()
        serializer = ServiceJobStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            transition_job_status(job, serializer.validated_data["status"], request.user)
            return Response({"success": True, "message": "Status updated."})
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=409)

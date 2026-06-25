from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer, UserCreateSerializer
from core.permissions import IsAdmin, IsServiceAdvisor
from apps.accounts.services import create_user, deactivate_user, activate_user
from apps.service_jobs.selectors import get_jobs_for_mechanic
from apps.service_jobs.serializers import ServiceJobSerializer


class MechanicViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(role="mechanic")
    serializer_class = UserSerializer
    filter_backends = [SearchFilter]
    search_fields = ["name", "email", "phone"]
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        create_user(
            name=serializer.validated_data["name"],
            email=serializer.validated_data["email"],
            phone=serializer.validated_data["phone"],
            role="mechanic",
            password=serializer.validated_data["password"],
            specialization=serializer.validated_data.get("specialization"),
        )

    @action(detail=True, methods=["patch"])
    def activate(self, request, pk=None):
        mechanic = self.get_object()
        activate_user(mechanic)
        return Response({"success": True, "message": "Mechanic activated."})

    @action(detail=True, methods=["patch"])
    def deactivate(self, request, pk=None):
        mechanic = self.get_object()
        from core.services import HasActiveDependentsError
        from apps.service_jobs.models import ServiceJob
        active_jobs = ServiceJob.objects.filter(
            assigned_mechanic=mechanic,
            status__in=["waiting", "in_progress", "waiting_for_parts", "rework_required"],
        )
        if active_jobs.exists():
            return Response(
                {"success": False, "message": f"Mechanic has {active_jobs.count()} active job(s). Reassign first."},
                status=409,
            )
        deactivate_user(mechanic)
        return Response({"success": True, "message": "Mechanic deactivated."})

    @action(detail=True, methods=["get"])
    def assigned_vehicles(self, request, pk=None):
        jobs = get_jobs_for_mechanic(pk)
        serializer = ServiceJobSerializer(jobs, many=True)
        return Response({"success": True, "data": serializer.data})

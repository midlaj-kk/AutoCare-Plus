from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import PartUsed
from .serializers import PartUsedSerializer, PartUsedCreateSerializer
from core.permissions import IsAdmin, IsMechanic
from apps.service_jobs.permissions import IsMechanicForAssignedJob
from apps.inventory.services import consume_part, restore_part
from apps.inventory.services import InsufficientStockError


class PartUsedViewSet(viewsets.ModelViewSet):
    serializer_class = PartUsedSerializer
    queryset = PartUsed.objects.none()

    def get_queryset(self):
        qs = PartUsed.objects.select_related("part", "service_job")
        if self.request.user.role == "mechanic":
            return qs.filter(service_job__assigned_mechanic=self.request.user)
        return qs

    def get_permissions(self):
        if self.action in ("create",):
            return [IsMechanic(), IsMechanicForAssignedJob()]
        if self.action in ("destroy",):
            return [IsMechanic(), IsMechanicForAssignedJob()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = PartUsedCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            from apps.service_jobs.models import ServiceJob
            job_id = serializer.validated_data.get("job_id") or request.data.get("service_job")
            job = ServiceJob.objects.get(id=job_id)
            part_used = consume_part(
                job,
                serializer.validated_data["part_id"],
                serializer.validated_data["quantity"],
                request.user,
            )
            output = PartUsedSerializer(part_used, context={"request": request})
            return Response(
                {"success": True, "message": "Part used recorded.", "data": output.data},
                status=status.HTTP_201_CREATED,
            )
        except InsufficientStockError as e:
            return Response({"success": False, "message": str(e)}, status=409)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        restore_part(instance, request.user)
        return Response(
            {"success": True, "message": "Part usage removed and stock restored."},
            status=status.HTTP_200_OK,
        )

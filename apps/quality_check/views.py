from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import QualityCheck
from .serializers import QualityCheckSerializer
from core.permissions import IsAdmin, IsServiceAdvisor
from .services import submit_quality_check, update_quality_check


class QualityCheckViewSet(viewsets.ModelViewSet):
    queryset = QualityCheck.objects.select_related("service_job", "checked_by")
    serializer_class = QualityCheckSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        from apps.service_jobs.models import ServiceJob
        job = ServiceJob.objects.get(id=serializer.validated_data.pop("service_job").id)
        submit_quality_check(job, serializer.validated_data, self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job_id = request.data.get("service_job")
        from apps.service_jobs.models import ServiceJob
        try:
            job = ServiceJob.objects.get(id=job_id)
            qc = submit_quality_check(job, serializer.validated_data, request.user)
            output = QualityCheckSerializer(qc, context={"request": request})
            return Response(
                {"success": True, "message": "Quality check submitted.", "data": output.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

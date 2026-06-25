from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Bill
from .serializers import BillSerializer, BillCreateSerializer
from core.permissions import IsCashier, IsAdmin
from .services import create_bill, update_bill


class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.select_related("service_job")
    serializer_class = BillSerializer
    permission_classes = [IsCashier]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["payment_status"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsCashier()]
        return [IsCashier()]

    def create(self, request, *args, **kwargs):
        serializer = BillCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.service_jobs.models import ServiceJob
        job_id = request.data.get("service_job")
        try:
            job = ServiceJob.objects.get(id=job_id)
            bill = create_bill(job, serializer.validated_data, request.user)
            output = BillSerializer(bill, context={"request": request})
            return Response(
                {"success": True, "message": "Bill created.", "data": output.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

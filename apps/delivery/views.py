from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Delivery
from .serializers import DeliverySerializer, DeliveryCreateSerializer
from core.permissions import IsCashier
from .services import complete_delivery


class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.select_related("service_job", "delivered_by")
    serializer_class = DeliverySerializer
    permission_classes = [IsCashier]

    def create(self, request, *args, **kwargs):
        serializer = DeliveryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.service_jobs.models import ServiceJob
        job_id = request.data.get("service_job")
        try:
            job = ServiceJob.objects.get(id=job_id)
            delivery = complete_delivery(job, serializer.validated_data, request.user)
            output = DeliverySerializer(delivery, context={"request": request})
            return Response(
                {"success": True, "message": "Delivery completed.", "data": output.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

    @action(detail=False, methods=["get"])
    def ready(self, request):
        from apps.service_jobs.models import ServiceJob
        jobs = ServiceJob.objects.filter(status="ready_for_delivery").select_related("vehicle", "vehicle__customer")
        from apps.service_jobs.serializers import ServiceJobSerializer
        serializer = ServiceJobSerializer(jobs, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def delivered(self, request):
        queryset = self.get_queryset()
        date = request.query_params.get("date")
        if date:
            queryset = queryset.filter(delivery_date__date=date)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

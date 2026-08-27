from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions import IsServiceAdvisor
from .selectors import get_vehicle_history, get_vehicle_history_by_number, get_customer_history
from apps.service_jobs.serializers import ServiceJobSerializer


class VehicleHistoryView(APIView):
    permission_classes = [IsServiceAdvisor]

    def get(self, request, vehicle_id=None):
        vehicle_number = request.query_params.get("vehicle_number")
        if vehicle_number:
            jobs = get_vehicle_history_by_number(vehicle_number)
        elif vehicle_id:
            jobs = get_vehicle_history(vehicle_id)
        else:
            return Response(
                {"success": False, "message": "Provide vehicle_id or vehicle_number."},
                status=400,
            )

        serializer = ServiceJobSerializer(jobs, many=True)
        return Response({"success": True, "data": serializer.data})


class CustomerHistoryView(APIView):
    permission_classes = [IsServiceAdvisor]

    def get(self, request, customer_id=None):
        jobs = get_customer_history(customer_id)
        data = []
        for job in jobs:
            data.append({
                "job_number": job.job_number,
                "vehicle": str(job.vehicle),
                "service_type": job.service_type,
                "status": job.status,
                "created_at": job.created_at,
                "mechanic": job.assigned_mechanic.name if job.assigned_mechanic else None,
            })
        return Response({"success": True, "data": data})

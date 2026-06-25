from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions import IsAdmin
from .selectors import (
    daily_revenue, monthly_revenue, completed_services,
    mechanic_productivity, spare_parts_usage,
)


class DailyRevenueReport(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        date = request.query_params.get("date")
        data = daily_revenue(date)
        return Response({"success": True, "data": data})


class MonthlyRevenueReport(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        if not month or not year:
            return Response({"success": False, "message": "month and year required"}, status=400)
        data = monthly_revenue(int(month), int(year))
        return Response({"success": True, "data": data})


class CompletedServicesReport(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        if not from_date or not to_date:
            return Response({"success": False, "message": "from and to dates required"}, status=400)
        count = completed_services(from_date, to_date)
        return Response({"success": True, "data": {"completed_count": count}})


class MechanicProductivityReport(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        if not from_date or not to_date:
            return Response({"success": False, "message": "from and to dates required"}, status=400)
        data = mechanic_productivity(from_date, to_date)
        return Response({"success": True, "data": list(data)})


class SparePartsUsageReport(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        if not from_date or not to_date:
            return Response({"success": False, "message": "from and to dates required"}, status=400)
        data = spare_parts_usage(from_date, to_date)
        return Response({"success": True, "data": list(data)})

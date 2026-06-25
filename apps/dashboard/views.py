from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions import IsAdmin
from .selectors import get_admin_summary


class DashboardSummaryView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        summary = get_admin_summary()
        return Response({"success": True, "data": summary})

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer
from core.permissions import IsCashier
from .services import record_payment


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("bill", "received_by")
    serializer_class = PaymentSerializer
    permission_classes = [IsCashier]

    def create(self, request, *args, **kwargs):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.billing.models import Bill
        bill_id = request.data.get("bill")
        try:
            bill = Bill.objects.get(id=bill_id)
            record_payment(
                bill,
                serializer.validated_data["paid_amount"],
                serializer.validated_data["payment_method"],
                serializer.validated_data["payment_date"],
                request.user,
            )
            return Response({"success": True, "message": "Payment recorded."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        from apps.billing.models import Bill
        bills = Bill.objects.filter(payment_status__in=["pending", "partial"])
        from apps.billing.serializers import BillSerializer
        serializer = BillSerializer(bills, many=True)
        return Response({"success": True, "data": serializer.data})

import json
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RazorpayOrder
from .serializers import (
    RazorpayOrderDetailSerializer,
    RazorpayOrderSerializer,
    RazorpayVerifySerializer,
)
from .razorpay_services import (
    RazorpayError,
    confirm_razorpay_payment,
    create_razorpay_order,
    process_webhook_event,
    verify_webhook_signature,
)
from core.permissions import IsCashier


class RazorpayViewSet(viewsets.ViewSet):
    permission_classes = [IsCashier]

    @action(detail=False, methods=["post"], url_path="order")
    def create_order(self, request):
        serializer = RazorpayOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bill = serializer.validated_data["bill"]
        try:
            order = create_razorpay_order(bill, request.user)
        except RazorpayError as e:
            return Response({"success": False, "message": str(e)}, status=400)
        return Response(
            {
                "success": True,
                "data": {
                    "order_id": order.order_id,
                    "amount": order.amount,
                    "currency": order.currency,
                    "key_id": settings.RAZORPAY_KEY_ID,
                    "bill": order.bill.id,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="verify")
    def verify(self, request):
        serializer = RazorpayVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.validated_data["razorpay_order_id"]
        try:
            bill = confirm_razorpay_payment(
                order,
                serializer.validated_data["razorpay_payment_id"],
                serializer.validated_data["razorpay_signature"],
            )
        except RazorpayError as e:
            return Response({"success": False, "message": str(e)}, status=400)
        return Response(
            {
                "success": True,
                "message": "Payment verified successfully.",
                "data": {"bill": bill.id, "payment_status": bill.payment_status},
            }
        )

    @action(detail=False, methods=["get"], url_path="status")
    def status(self, request):
        order_id = request.query_params.get("order_id")
        if not order_id:
            return Response(
                {"success": False, "message": "order_id is required."}, status=400
            )
        try:
            order = RazorpayOrder.objects.select_related("bill").get(order_id=order_id)
        except RazorpayOrder.DoesNotExist:
            return Response(
                {"success": False, "message": "Order not found."}, status=404
            )
        serializer = RazorpayOrderDetailSerializer(order)
        return Response({"success": True, "data": serializer.data})


class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature", "")
        try:
            verify_webhook_signature(request.body, signature)
            data = json.loads(request.body)
        except (RazorpayError, ValueError) as e:
            return Response({"success": False, "message": str(e)}, status=400)

        event = data.get("event")
        entity = data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = entity.get("order_id")
        if event and order_id:
            process_webhook_event(event, entity, order_id)
        return Response({"success": True})

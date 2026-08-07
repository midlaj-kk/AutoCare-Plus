from decimal import Decimal
from rest_framework import serializers
from .models import Payment, RazorpayOrder


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class PaymentCreateSerializer(serializers.Serializer):
    bill = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=["cash", "upi", "card", "bank_transfer"])
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    payment_date = serializers.DateField()


class RazorpayOrderSerializer(serializers.Serializer):
    bill = serializers.IntegerField()

    def validate_bill(self, value):
        from apps.billing.models import Bill
        try:
            return Bill.objects.get(id=value)
        except Bill.DoesNotExist:
            raise serializers.ValidationError("Bill not found.")


class RazorpayVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

    def validate_razorpay_order_id(self, value):
        try:
            return RazorpayOrder.objects.select_related("bill").get(order_id=value)
        except RazorpayOrder.DoesNotExist:
            raise serializers.ValidationError("Razorpay order not found.")


class RazorpayOrderDetailSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="bill.invoice_number", read_only=True)

    class Meta:
        model = RazorpayOrder
        fields = (
            "id",
            "order_id",
            "bill",
            "invoice_number",
            "amount",
            "currency",
            "status",
            "created_at",
        )

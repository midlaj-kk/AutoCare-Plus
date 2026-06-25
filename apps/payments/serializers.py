from decimal import Decimal
from rest_framework import serializers
from .models import Payment


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

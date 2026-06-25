from decimal import Decimal
from rest_framework import serializers
from .models import Bill


class BillSerializer(serializers.ModelSerializer):
    job_number = serializers.CharField(source="service_job.job_number", read_only=True)

    class Meta:
        model = Bill
        fields = "__all__"
        read_only_fields = ("id", "invoice_number", "total_amount", "payment_status", "created_at", "updated_at")


class BillCreateSerializer(serializers.Serializer):
    service_job = serializers.IntegerField()
    labour_charge = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    parts_charge = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

from decimal import Decimal
from rest_framework import serializers
from .models import PartUsed


class PartUsedSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)
    part_number = serializers.CharField(source="part.part_number", read_only=True)

    class Meta:
        model = PartUsed
        fields = (
            "id", "service_job", "part", "part_name", "part_number",
            "quantity", "price", "added_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "price", "added_by", "created_at", "updated_at")


class PartUsedCreateSerializer(serializers.Serializer):
    service_job = serializers.IntegerField()
    part_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))

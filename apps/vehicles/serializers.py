from rest_framework import serializers
from .models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class VehicleListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Vehicle
        fields = ("id", "vehicle_number", "brand", "model", "year", "customer_name", "status")

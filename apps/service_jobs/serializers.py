from rest_framework import serializers
from .models import ServiceJob


class ServiceJobSerializer(serializers.ModelSerializer):
    vehicle_number = serializers.CharField(source="vehicle.vehicle_number", read_only=True)
    customer_name = serializers.CharField(source="vehicle.customer.name", read_only=True)
    mechanic_name = serializers.CharField(source="assigned_mechanic.name", read_only=True)

    class Meta:
        model = ServiceJob
        fields = (
            "id", "job_number", "vehicle", "vehicle_number", "customer_name",
            "complaint", "service_type", "assigned_mechanic", "mechanic_name",
            "created_by", "status", "odometer_reading", "created_at", "updated_at",
        )
        read_only_fields = ("id", "job_number", "created_by", "created_at", "updated_at")


class ServiceJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceJob
        fields = (
            "vehicle", "complaint", "service_type",
            "assigned_mechanic", "odometer_reading",
        )


class ServiceJobStatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class AssignMechanicSerializer(serializers.Serializer):
    mechanic_id = serializers.IntegerField()

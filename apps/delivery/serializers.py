from rest_framework import serializers
from .models import Delivery


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class DeliveryCreateSerializer(serializers.Serializer):
    service_job = serializers.IntegerField()
    delivery_date = serializers.DateTimeField()
    customer_received = serializers.BooleanField(default=False)
    remarks = serializers.CharField(required=False, allow_blank=True)

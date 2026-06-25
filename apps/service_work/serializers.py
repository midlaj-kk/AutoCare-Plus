from rest_framework import serializers
from .models import ServiceWork


class ServiceWorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceWork
        fields = "__all__"
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class ServiceWorkStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["pending", "in_progress", "completed"])

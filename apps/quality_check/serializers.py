from rest_framework import serializers
from .models import QualityCheck


class QualityCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityCheck
        fields = "__all__"
        read_only_fields = ("id", "checked_by", "created_at", "updated_at")

from rest_framework import serializers


class ServiceHistorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    job_number = serializers.CharField()
    service_type = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    mechanic_name = serializers.CharField()
    total_labour = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_parts = serializers.DecimalField(max_digits=10, decimal_places=2)

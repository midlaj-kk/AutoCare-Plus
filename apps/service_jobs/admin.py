from django.contrib import admin
from .models import ServiceJob


@admin.register(ServiceJob)
class ServiceJobAdmin(admin.ModelAdmin):
    list_display = ("job_number", "vehicle", "status", "assigned_mechanic", "created_at")
    list_filter = ("status", "service_type")
    search_fields = ("job_number", "vehicle__vehicle_number")

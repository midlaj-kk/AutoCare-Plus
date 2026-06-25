from django.contrib import admin
from .models import ServiceWork


@admin.register(ServiceWork)
class ServiceWorkAdmin(admin.ModelAdmin):
    list_display = ("work_name", "service_job", "status", "labour_charge")
    list_filter = ("status",)

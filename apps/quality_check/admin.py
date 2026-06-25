from django.contrib import admin
from .models import QualityCheck


@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = ("service_job", "overall_status", "checked_by", "created_at")
    list_filter = ("overall_status",)

from django.contrib import admin
from .models import PartUsed


@admin.register(PartUsed)
class PartUsedAdmin(admin.ModelAdmin):
    list_display = ("service_job", "part", "quantity", "price", "created_at")
    search_fields = ("service_job__job_number", "part__name")

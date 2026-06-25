from django.contrib import admin
from .models import Bill


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "service_job", "total_amount", "payment_status", "created_at")
    list_filter = ("payment_status",)
    search_fields = ("invoice_number", "service_job__job_number")

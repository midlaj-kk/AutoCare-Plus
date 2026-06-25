from django.contrib import admin
from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("service_job", "delivered_by", "delivery_date", "customer_received")
    list_filter = ("customer_received",)

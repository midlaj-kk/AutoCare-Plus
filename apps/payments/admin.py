from django.contrib import admin
from .models import Payment, RazorpayOrder


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("bill", "payment_method", "paid_amount", "payment_date", "received_by")
    list_filter = ("payment_method", "payment_date")


@admin.register(RazorpayOrder)
class RazorpayOrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "bill", "amount", "currency", "status", "created_by", "created_at")
    list_filter = ("status", "currency")
    readonly_fields = ("created_at", "updated_at")

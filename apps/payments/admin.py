from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("bill", "payment_method", "paid_amount", "payment_date", "received_by")
    list_filter = ("payment_method", "payment_date")

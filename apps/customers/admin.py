from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "status", "created_at")
    search_fields = ("name", "phone", "email")
    list_filter = ("status",)

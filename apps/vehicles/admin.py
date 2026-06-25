from django.contrib import admin
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("vehicle_number", "brand", "model", "customer", "status")
    search_fields = ("vehicle_number", "brand", "model")
    list_filter = ("status", "brand")

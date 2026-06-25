from django.contrib import admin
from .models import SparePart, StockMovement


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ("name", "part_number", "stock_quantity", "selling_price", "status")
    search_fields = ("name", "part_number")
    list_filter = ("status",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("spare_part", "movement_type", "quantity", "reference_type", "created_at")
    list_filter = ("movement_type", "reference_type")

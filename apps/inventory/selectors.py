from django.db import models
from .models import SparePart, StockMovement


def get_spare_parts(search=None, status=None):
    qs = SparePart.objects.all()
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(part_number__icontains=search)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_low_stock_parts():
    return SparePart.objects.filter(
        stock_quantity__lte=models.F("minimum_stock"),
        status="active",
    )


def get_stock_history(part_id):
    return StockMovement.objects.filter(spare_part_id=part_id).select_related(
        "created_by"
    )

from django.db import models
from core.models import TimeStampedModel


class SparePart(TimeStampedModel):
    name = models.CharField(max_length=150)
    part_number = models.CharField(max_length=50, unique=True)
    stock_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    unit = models.CharField(max_length=20)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=10,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )

    def __str__(self):
        return f"{self.name} ({self.part_number})"


class StockMovement(models.Model):
    spare_part = models.ForeignKey(
        SparePart, on_delete=models.CASCADE, related_name="movements"
    )
    movement_type = models.CharField(
        max_length=10, choices=[("in", "In"), ("out", "Out")]
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reference_type = models.CharField(
        max_length=20,
        choices=[
            ("purchase", "Purchase"),
            ("service_job", "Service Job"),
            ("adjustment", "Adjustment"),
        ],
    )
    reference_id = models.BigIntegerField(blank=True, null=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="stock_movements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.movement_type} {self.quantity} of {self.spare_part.name}"

from django.db import models
from core.models import TimeStampedModel


class Vehicle(TimeStampedModel):
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="vehicles",
    )
    vehicle_number = models.CharField(max_length=20, unique=True, db_index=True)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    kilometers = models.IntegerField(default=0)
    status = models.CharField(
        max_length=10,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )

    def __str__(self):
        return f"{self.vehicle_number} - {self.brand} {self.model}"

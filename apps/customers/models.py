from django.db import models
from core.models import TimeStampedModel
from core.validators import validate_phone


class Customer(TimeStampedModel):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, db_index=True, validators=[validate_phone])
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )

    class Meta:
        verbose_name_plural = "customers"

    def __str__(self):
        return f"{self.name} ({self.phone})"

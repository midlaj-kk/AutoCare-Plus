from django.db import models
from core.models import TimeStampedModel


class Bill(TimeStampedModel):
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    service_job = models.OneToOneField(
        "service_jobs.ServiceJob",
        on_delete=models.PROTECT,
        related_name="bill",
    )
    labour_charge = models.DecimalField(max_digits=10, decimal_places=2)
    parts_charge = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("partial", "Partial"),
        ],
        default="pending",
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="created_bills"
    )

    def __str__(self):
        return self.invoice_number

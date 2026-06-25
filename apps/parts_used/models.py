from django.db import models
from core.models import TimeStampedModel


class PartUsed(TimeStampedModel):
    service_job = models.ForeignKey(
        "service_jobs.ServiceJob",
        on_delete=models.CASCADE,
        related_name="parts_used",
    )
    part = models.ForeignKey(
        "inventory.SparePart", on_delete=models.PROTECT, related_name="parts_used"
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    added_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="added_parts"
    )

    def __str__(self):
        return f"{self.part.name} x{self.quantity}"

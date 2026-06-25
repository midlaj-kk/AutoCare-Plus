from django.db import models
from core.models import TimeStampedModel
from core.constants import WORK_STATUS_CHOICES, WORK_STATUS_PENDING


class ServiceWork(TimeStampedModel):
    service_job = models.ForeignKey(
        "service_jobs.ServiceJob",
        on_delete=models.CASCADE,
        related_name="works",
    )
    work_name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=15, choices=WORK_STATUS_CHOICES, default=WORK_STATUS_PENDING
    )
    labour_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="created_works"
    )

    def __str__(self):
        return f"{self.work_name} - {self.service_job.job_number}"

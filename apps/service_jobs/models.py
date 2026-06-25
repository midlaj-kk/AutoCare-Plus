from django.db import models
from core.models import TimeStampedModel
from core.constants import JOB_STATUS_CHOICES, JOB_STATUS_WAITING


class ServiceJob(TimeStampedModel):
    job_number = models.CharField(max_length=20, unique=True, editable=False)
    vehicle = models.ForeignKey(
        "vehicles.Vehicle", on_delete=models.PROTECT, related_name="service_jobs"
    )
    complaint = models.TextField()
    service_type = models.CharField(max_length=50)
    assigned_mechanic = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_jobs",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_jobs",
    )
    status = models.CharField(
        max_length=20, choices=JOB_STATUS_CHOICES, default=JOB_STATUS_WAITING
    )
    odometer_reading = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.job_number

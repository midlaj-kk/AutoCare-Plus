from django.db import models
from core.models import TimeStampedModel


class QualityCheck(TimeStampedModel):
    STATUS_CHOICES = [
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("na", "N/A"),
    ]
    OIL_CHOICES = [
        ("no_issue", "No Issue"),
        ("issue_found", "Issue Found"),
        ("na", "N/A"),
    ]
    OVERALL_CHOICES = [
        ("approved", "Approved"),
        ("rework_required", "Rework Required"),
    ]

    service_job = models.OneToOneField(
        "service_jobs.ServiceJob",
        on_delete=models.CASCADE,
        related_name="quality_check",
    )
    brake_check = models.CharField(max_length=15, choices=STATUS_CHOICES)
    engine_check = models.CharField(max_length=15, choices=STATUS_CHOICES)
    oil_leakage_check = models.CharField(max_length=15, choices=OIL_CHOICES)
    ac_check = models.CharField(max_length=15, choices=STATUS_CHOICES)
    tyre_check = models.CharField(max_length=15, choices=STATUS_CHOICES)
    test_drive = models.CharField(max_length=15, choices=STATUS_CHOICES)
    overall_status = models.CharField(max_length=20, choices=OVERALL_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    checked_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="quality_checks"
    )

    def __str__(self):
        return f"QC - {self.service_job.job_number} ({self.overall_status})"

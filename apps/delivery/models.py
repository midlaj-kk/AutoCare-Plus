from django.db import models


class Delivery(models.Model):
    service_job = models.OneToOneField(
        "service_jobs.ServiceJob",
        on_delete=models.PROTECT,
        related_name="delivery",
    )
    delivered_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="deliveries"
    )
    delivery_date = models.DateTimeField()
    customer_received = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Delivery - {self.service_job.job_number}"

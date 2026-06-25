from .models import Delivery
from apps.service_jobs.services import transition_job_status
from core.constants import JOB_STATUS_DELIVERED


def complete_delivery(job, data, actor):
    delivery = Delivery.objects.create(
        service_job=job,
        delivered_by=actor,
        delivery_date=data.get("delivery_date"),
        customer_received=data.get("customer_received", False),
        remarks=data.get("remarks", ""),
    )
    transition_job_status(job, JOB_STATUS_DELIVERED, actor)
    return delivery

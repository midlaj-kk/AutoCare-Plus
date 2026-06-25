from core.services import generate_sequential_code
from core.constants import (
    JOB_STATUS_WAITING,
    JOB_STATUS_IN_PROGRESS,
    JOB_STATUS_WAITING_FOR_PARTS,
    JOB_STATUS_QC_PENDING,
    JOB_STATUS_REWORK_REQUIRED,
    JOB_STATUS_READY_FOR_BILL,
    JOB_STATUS_READY_FOR_DELIVERY,
    JOB_STATUS_DELIVERED,
    JOB_STATUS_CANCELLED,
)


ALLOWED_TRANSITIONS = {
    JOB_STATUS_WAITING: {JOB_STATUS_IN_PROGRESS, JOB_STATUS_CANCELLED},
    JOB_STATUS_IN_PROGRESS: {JOB_STATUS_WAITING_FOR_PARTS, JOB_STATUS_QC_PENDING, JOB_STATUS_CANCELLED},
    JOB_STATUS_WAITING_FOR_PARTS: {JOB_STATUS_IN_PROGRESS, JOB_STATUS_CANCELLED},
    JOB_STATUS_QC_PENDING: {JOB_STATUS_READY_FOR_BILL, JOB_STATUS_REWORK_REQUIRED},
    JOB_STATUS_REWORK_REQUIRED: {JOB_STATUS_IN_PROGRESS},
    JOB_STATUS_READY_FOR_BILL: {JOB_STATUS_READY_FOR_DELIVERY, JOB_STATUS_CANCELLED},
    JOB_STATUS_READY_FOR_DELIVERY: {JOB_STATUS_DELIVERED},
    JOB_STATUS_DELIVERED: set(),
    JOB_STATUS_CANCELLED: set(),
}


class InvalidTransitionError(Exception):
    pass


def create_service_job(data, created_by):
    from .models import ServiceJob

    job_number = generate_sequential_code("SJ", ServiceJob)
    data["job_number"] = job_number
    data["created_by"] = created_by
    return ServiceJob.objects.create(**data)


def transition_job_status(job, new_status, actor=None):
    if new_status not in ALLOWED_TRANSITIONS.get(job.status, set()):
        raise InvalidTransitionError(
            f"Cannot move job from '{job.status}' to '{new_status}'."
        )
    if new_status == JOB_STATUS_CANCELLED:
        from apps.billing.models import Bill
        if Bill.objects.filter(service_job=job).exists():
            raise InvalidTransitionError(
                "Cannot cancel a job that already has a bill."
            )
    if new_status == JOB_STATUS_READY_FOR_DELIVERY:
        from apps.billing.models import Bill
        bill = Bill.objects.filter(service_job=job).first()
        if bill and bill.payment_status != "paid":
            raise InvalidTransitionError(
                "Cannot mark job ready for delivery until bill is fully paid."
            )
            raise InvalidTransitionError(
                "Cannot cancel a job that already has a bill."
            )

    job.status = new_status
    job.save(update_fields=["status", "updated_at"])
    return job


def assign_mechanic(job, mechanic_id):
    job.assigned_mechanic_id = mechanic_id
    if job.status == JOB_STATUS_WAITING:
        job.status = JOB_STATUS_IN_PROGRESS
    job.save(update_fields=["assigned_mechanic", "status", "updated_at"])
    return job


def change_mechanic(job, mechanic_id):
    job.assigned_mechanic_id = mechanic_id
    job.save(update_fields=["assigned_mechanic", "updated_at"])
    return job

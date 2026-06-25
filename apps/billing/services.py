from django.db import transaction
from django.db.models import Sum
from .models import Bill
from apps.service_jobs.services import transition_job_status
from core.constants import JOB_STATUS_READY_FOR_DELIVERY, JOB_STATUS_READY_FOR_BILL
from core.services import generate_sequential_code


def create_bill(job, data, created_by):
    if job.status != JOB_STATUS_READY_FOR_BILL:
        from apps.service_jobs.services import InvalidTransitionError
        raise InvalidTransitionError(
            "Job must be in 'ready_for_bill' status to create a bill."
        )

    labour = data.get("labour_charge", 0)
    parts = data.get("parts_charge", 0)
    tax = data.get("tax", 0)
    discount = data.get("discount", 0)
    total = labour + parts + tax - discount

    invoice_number = generate_sequential_code("INV", Bill, field_name="invoice_number")

    bill = Bill.objects.create(
        invoice_number=invoice_number,
        service_job=job,
        labour_charge=labour,
        parts_charge=parts,
        tax=tax,
        discount=discount,
        total_amount=total,
        created_by=created_by,
    )
    return bill


def update_bill(bill, data):
    if bill.payment_status != "pending":
        raise ValueError("Cannot update bill after payment has started.")

    labour = data.get("labour_charge", bill.labour_charge)
    parts = data.get("parts_charge", bill.parts_charge)
    tax = data.get("tax", bill.tax)
    discount = data.get("discount", bill.discount)
    total = labour + parts + tax - discount

    for field, value in data.items():
        setattr(bill, field, value)
    bill.total_amount = total
    bill.save()
    return bill


def recalculate_payment_status(bill):
    total_paid = bill.payments.aggregate(s=Sum("paid_amount"))["s"] or 0
    if total_paid >= bill.total_amount:
        bill.payment_status = "paid"
        bill.save(update_fields=["payment_status"])
        transition_job_status(bill.service_job, JOB_STATUS_READY_FOR_DELIVERY, None)
    elif total_paid > 0:
        bill.payment_status = "partial"
        bill.save(update_fields=["payment_status"])
    return bill

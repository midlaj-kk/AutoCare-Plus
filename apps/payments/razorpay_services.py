from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
import razorpay

from .models import Payment, RazorpayOrder
from apps.billing.services import recalculate_payment_status


class RazorpayError(Exception):
    pass


def get_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RazorpayError("Razorpay is not configured.")
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def get_remaining_amount(bill):
    total_paid = bill.payments.aggregate(s=Sum("paid_amount"))["s"] or 0
    return bill.total_amount - total_paid


@transaction.atomic
def create_razorpay_order(bill, actor, currency=None):
    amount = get_remaining_amount(bill)
    if amount <= 0:
        raise RazorpayError("This bill is already fully paid.")

    currency = currency or settings.RAZORPAY_CURRENCY
    client = get_client()
    data = {
        "amount": int(amount * 100),
        "currency": currency,
        "receipt": bill.invoice_number,
        "notes": {
            "bill_id": bill.id,
            "invoice_number": bill.invoice_number,
        },
    }
    try:
        response = client.order.create(data=data)
    except Exception as e:
        raise RazorpayError(f"Failed to create Razorpay order: {e}")

    return RazorpayOrder.objects.create(
        bill=bill,
        order_id=response["id"],
        amount=amount,
        currency=currency,
        status=RazorpayOrder.Status.CREATED,
        created_by=actor,
    )


def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    client = get_client()
    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
    except Exception:
        raise RazorpayError("Invalid payment signature.")


@transaction.atomic
def confirm_razorpay_payment(order, razorpay_payment_id, razorpay_signature):
    if order.status == RazorpayOrder.Status.PAID:
        raise RazorpayError("This order has already been processed.")

    verify_payment_signature(
        order.order_id, razorpay_payment_id, razorpay_signature
    )

    bill = order.bill
    order.status = RazorpayOrder.Status.PAID
    order.save(update_fields=["status"])

    Payment.objects.create(
        bill=bill,
        payment_method=Payment.Method.ONLINE,
        paid_amount=order.amount,
        payment_date=timezone.now().date(),
        received_by=order.created_by,
        razorpay_order=order,
        razorpay_payment_id=razorpay_payment_id,
    )
    recalculate_payment_status(bill)
    return bill


def verify_webhook_signature(payload, signature):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise RazorpayError("Razorpay webhook secret is not configured.")
    client = get_client()
    try:
        client.utility.verify_webhook_signature(
            payload, signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
    except Exception:
        raise RazorpayError("Invalid webhook signature.")


@transaction.atomic
def process_webhook_event(event, entity, order_id):
    order = RazorpayOrder.objects.filter(order_id=order_id).first()
    if not order:
        return None

    if event == "payment.captured" and order.status != RazorpayOrder.Status.PAID:
        order.status = RazorpayOrder.Status.PAID
        order.save(update_fields=["status"])
        Payment.objects.create(
            bill=order.bill,
            payment_method=Payment.Method.ONLINE,
            paid_amount=order.amount,
            payment_date=timezone.now().date(),
            received_by=order.created_by,
            razorpay_order=order,
            razorpay_payment_id=entity.get("id"),
        )
        recalculate_payment_status(order.bill)
        return order

    if event == "payment.failed" and order.status != RazorpayOrder.Status.PAID:
        order.status = RazorpayOrder.Status.FAILED
        order.save(update_fields=["status"])
        return order

    return None

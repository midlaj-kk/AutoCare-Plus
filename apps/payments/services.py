from django.db import transaction
from .models import Payment
from apps.billing.services import recalculate_payment_status


@transaction.atomic
def record_payment(bill, amount, method, payment_date, actor):
    Payment.objects.create(
        bill=bill,
        payment_method=method,
        paid_amount=amount,
        payment_date=payment_date,
        received_by=actor,
    )
    recalculate_payment_status(bill)
    return bill

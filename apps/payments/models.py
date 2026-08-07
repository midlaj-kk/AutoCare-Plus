from django.db import models


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        ONLINE = "online", "Online"

    bill = models.ForeignKey(
        "billing.Bill", on_delete=models.PROTECT, related_name="payments"
    )
    payment_method = models.CharField(max_length=20, choices=Method.choices)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    received_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="received_payments"
    )
    razorpay_order = models.ForeignKey(
        "payments.RazorpayOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} {self.paid_amount} for {self.bill.invoice_number}"


class RazorpayOrder(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        ATTEMPTED = "attempted", "Attempted"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    bill = models.ForeignKey(
        "billing.Bill", on_delete=models.PROTECT, related_name="razorpay_orders"
    )
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CREATED
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="razorpay_orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_id

from django.db import models


class Payment(models.Model):
    bill = models.ForeignKey(
        "billing.Bill", on_delete=models.PROTECT, related_name="payments"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("cash", "Cash"),
            ("upi", "UPI"),
            ("card", "Card"),
            ("bank_transfer", "Bank Transfer"),
        ],
    )
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    received_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="received_payments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} {self.paid_amount} for {self.bill.invoice_number}"

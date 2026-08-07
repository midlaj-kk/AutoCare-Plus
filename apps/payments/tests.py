from unittest.mock import patch
from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from rest_framework import status as http_status

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.service_jobs.models import ServiceJob
from apps.billing.services import create_bill
from apps.payments.models import Payment, RazorpayOrder
from apps.payments.razorpay_services import (
    RazorpayError,
    confirm_razorpay_payment,
    create_razorpay_order,
    process_webhook_event,
)

RAZORPAY_SETTINGS = dict(
    RAZORPAY_KEY_ID="rzp_test_key",
    RAZORPAY_KEY_SECRET="test_secret",
    RAZORPAY_WEBHOOK_SECRET="test_webhook_secret",
    RAZORPAY_CURRENCY="INR",
)


class FakeOrderResource:
    def create(self, data):
        return {
            "id": "order_123",
            "amount": data["amount"],
            "currency": data["currency"],
        }


class FakeUtility:
    def verify_payment_signature(self, data):
        if data.get("razorpay_signature") != "valid_signature":
            raise RazorpayError("Invalid payment signature.")
        return True

    def verify_webhook_signature(self, body, signature, secret):
        if signature != "valid_webhook_signature":
            raise RazorpayError("Invalid webhook signature.")
        return True


class FakeClient:
    def __init__(self):
        self.order = FakeOrderResource()
        self.utility = FakeUtility()


class RazorpayTestCaseMixin:
    def setUp(self):
        self.cashier = User.objects.create_user(
            username="cashier1",
            email="cashier1@example.com",
            password="testpass123",
            name="Cashier One",
            phone="9876543210",
            role="cashier",
        )
        self.other_user = User.objects.create_user(
            username="mechanic1",
            email="mechanic1@example.com",
            password="testpass123",
            name="Mechanic One",
            phone="9876543211",
            role="mechanic",
        )
        self.customer = Customer.objects.create(
            name="Test Customer", phone="9999999999"
        )
        self.vehicle = Vehicle.objects.create(
            customer=self.customer,
            vehicle_number="KA01AB1234",
            brand="Honda",
            model="City",
        )
        self.job = ServiceJob.objects.create(
            vehicle=self.vehicle,
            complaint="Engine noise",
            service_type="Full service",
            created_by=self.cashier,
            status="ready_for_bill",
        )
        self.bill = create_bill(
            self.job,
            {"labour_charge": Decimal("1000.00"), "parts_charge": Decimal("500.00")},
            self.cashier,
        )
        self.create_order_patch = patch(
            "apps.payments.razorpay_services.get_client",
            return_value=FakeClient(),
        )
        self.create_order_patch.start()
        self.addCleanup(self.create_order_patch.stop)


@override_settings(**RAZORPAY_SETTINGS)
class RazorpayOrderAPITest(RazorpayTestCaseMixin, APITestCase):
    def test_create_order_success(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(
            "/api/v1/razorpay/order/", {"bill": self.bill.id}, format="json"
        )
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        data = response.data["data"]
        self.assertEqual(data["order_id"], "order_123")
        self.assertEqual(data["amount"], Decimal("1500.00"))
        self.assertEqual(data["currency"], "INR")
        self.assertEqual(data["key_id"], "rzp_test_key")
        order = RazorpayOrder.objects.get(order_id="order_123")
        self.assertEqual(order.bill, self.bill)
        self.assertEqual(order.status, "created")

    def test_create_order_rejects_fully_paid_bill(self):
        Payment.objects.create(
            bill=self.bill,
            payment_method="cash",
            paid_amount=self.bill.total_amount,
            payment_date="2026-08-07",
            received_by=self.cashier,
        )
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(
            "/api/v1/razorpay/order/", {"bill": self.bill.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_create_order_requires_cashier(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            "/api/v1/razorpay/order/", {"bill": self.bill.id}, format="json"
        )
        self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)


@override_settings(**RAZORPAY_SETTINGS)
class RazorpayVerifyAPITest(RazorpayTestCaseMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.order = create_razorpay_order(self.bill, self.cashier)

    def test_verify_success(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(
            "/api/v1/razorpay/verify/",
            {
                "razorpay_order_id": self.order.order_id,
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "valid_signature",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["payment_status"], "paid")
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.payment_status, "paid")
        payment = Payment.objects.get(razorpay_payment_id="pay_123")
        self.assertEqual(payment.payment_method, "online")
        self.assertEqual(payment.paid_amount, self.bill.total_amount)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")

    def test_verify_invalid_signature(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(
            "/api/v1/razorpay/verify/",
            {
                "razorpay_order_id": self.order.order_id,
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "bad_signature",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.filter(razorpay_payment_id="pay_123").exists())

    def test_verify_already_processed(self):
        confirm_razorpay_payment(self.order, "pay_123", "valid_signature")
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(
            "/api/v1/razorpay/verify/",
            {
                "razorpay_order_id": self.order.order_id,
                "razorpay_payment_id": "pay_456",
                "razorpay_signature": "valid_signature",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.filter(razorpay_payment_id="pay_456").exists())


@override_settings(**RAZORPAY_SETTINGS)
class RazorpayStatusAPITest(RazorpayTestCaseMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.order = create_razorpay_order(self.bill, self.cashier)

    def test_status_returns_order(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get(
            f"/api/v1/razorpay/status/?order_id={self.order.order_id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["order_id"], self.order.order_id)

    def test_status_requires_order_id(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get("/api/v1/razorpay/status/")
        self.assertEqual(response.status_code, 400)

    def test_status_unknown_order(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get("/api/v1/razorpay/status/?order_id=unknown")
        self.assertEqual(response.status_code, 404)


@override_settings(**RAZORPAY_SETTINGS)
class RazorpayWebhookAPITest(RazorpayTestCaseMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.order = create_razorpay_order(self.bill, self.cashier)

    def test_webhook_invalid_signature(self):
        response = self.client.post(
            "/api/v1/razorpay/webhook/",
            {"event": "payment.captured"},
            format="json",
            HTTP_X_RAZORPAY_SIGNATURE="bad_signature",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.exists())

    def test_webhook_payment_captured(self):
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook_1",
                        "order_id": self.order.order_id,
                        "amount": 150000,
                    }
                }
            },
        }
        response = self.client.post(
            "/api/v1/razorpay/webhook/",
            payload,
            format="json",
            HTTP_X_RAZORPAY_SIGNATURE="valid_webhook_signature",
        )
        self.assertEqual(response.status_code, 200)
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.payment_status, "paid")
        payment = Payment.objects.get(razorpay_payment_id="pay_webhook_1")
        self.assertEqual(payment.payment_method, "online")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")

    def test_webhook_payment_failed(self):
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail_1",
                        "order_id": self.order.order_id,
                    }
                }
            },
        }
        response = self.client.post(
            "/api/v1/razorpay/webhook/",
            payload,
            format="json",
            HTTP_X_RAZORPAY_SIGNATURE="valid_webhook_signature",
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "failed")
        self.assertFalse(Payment.objects.exists())


@override_settings(**RAZORPAY_SETTINGS)
class RazorpayServiceTest(RazorpayTestCaseMixin, TestCase):
    def test_create_order_raises_when_not_configured(self):
        with patch(
            "apps.payments.razorpay_services.get_client",
            side_effect=RazorpayError("Razorpay is not configured."),
        ):
            with self.assertRaises(RazorpayError):
                create_razorpay_order(self.bill, self.cashier)

    def test_confirm_records_payment_and_recalculates(self):
        order = create_razorpay_order(self.bill, self.cashier)
        bill = confirm_razorpay_payment(order, "pay_123", "valid_signature")
        bill.refresh_from_db()
        self.assertEqual(bill.payment_status, "paid")

    def test_webhook_event_unknown_order(self):
        result = process_webhook_event(
            "payment.captured", {"id": "pay_1", "order_id": "order_unknown"}, "order_unknown"
        )
        self.assertIsNone(result)

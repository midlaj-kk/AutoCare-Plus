from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.service_jobs.models import ServiceJob


class VehicleHistoryAPITest(APITestCase):
    def setUp(self):
        self.advisor = User.objects.create_user(
            username="advisor1",
            email="advisor1@example.com",
            password="testpass123",
            name="Advisor One",
            phone="9876543201",
            role="service_advisor",
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
            created_by=self.advisor,
        )
        self.client.force_authenticate(user=self.advisor)

    def test_vehicle_history_returns_fields_frontend_needs(self):
        response = self.client.get(f"/api/v1/vehicles/{self.vehicle.id}/history/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(len(data), 1)
        item = data[0]
        # Fields that ServiceJobModel.fromJson() casts with `as int`.
        self.assertIsInstance(item["id"], int)
        self.assertIsInstance(item["vehicle"], int)
        # Fields that ServiceJobModel.fromJson() casts with `as String`.
        self.assertIsInstance(item["job_number"], str)
        self.assertIsInstance(item["service_type"], str)
        self.assertIsInstance(item["complaint"], str)
        self.assertIsInstance(item["status"], str)

from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.service_jobs.models import ServiceJob


class ServiceJobAPITestCase(APITestCase):
    def setUp(self):
        self.advisor = User.objects.create_user(
            username="advisor1",
            email="advisor1@example.com",
            password="testpass123",
            name="Advisor One",
            phone="9876543201",
            role="service_advisor",
        )
        self.mechanic = User.objects.create_user(
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
            created_by=self.advisor,
        )
        self.client.force_authenticate(user=self.advisor)


class AssignMechanicAPITest(ServiceJobAPITestCase):
    def test_assign_mechanic_success(self):
        response = self.client.patch(
            f"/api/v1/service-jobs/{self.job.id}/assign_mechanic/",
            {"mechanic_id": self.mechanic.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.job.refresh_from_db()
        self.assertEqual(self.job.assigned_mechanic, self.mechanic)
        self.assertEqual(self.job.status, "in_progress")

    def test_assign_mechanic_unknown_mechanic(self):
        response = self.client.patch(
            f"/api/v1/service-jobs/{self.job.id}/assign_mechanic/",
            {"mechanic_id": 99999},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data["success"])
        self.job.refresh_from_db()
        self.assertIsNone(self.job.assigned_mechanic)

    def test_assign_mechanic_non_mechanic_role(self):
        response = self.client.patch(
            f"/api/v1/service-jobs/{self.job.id}/assign_mechanic/",
            {"mechanic_id": self.advisor.id},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.job.refresh_from_db()
        self.assertIsNone(self.job.assigned_mechanic)


class ChangeMechanicAPITest(ServiceJobAPITestCase):
    def setUp(self):
        super().setUp()
        self.job.assigned_mechanic = self.mechanic
        self.job.save(update_fields=["assigned_mechanic"])

    def test_change_mechanic_unknown_mechanic(self):
        response = self.client.patch(
            f"/api/v1/service-jobs/{self.job.id}/change_mechanic/",
            {"mechanic_id": 12345},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.job.refresh_from_db()
        self.assertEqual(self.job.assigned_mechanic, self.mechanic)


class TransitionJobStatusTest(ServiceJobAPITestCase):
    def test_invalid_transition_returns_409(self):
        response = self.client.patch(
            f"/api/v1/service-jobs/{self.job.id}/status/",
            {"status": "delivered"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "waiting")

    def test_valid_transition(self):
        response = self.client.patch(
            f"/api/v1/service-jobs/{self.job.id}/status/",
            {"status": "in_progress"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "in_progress")

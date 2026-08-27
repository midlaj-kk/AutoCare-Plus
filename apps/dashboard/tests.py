from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.service_jobs.models import ServiceJob


class DashboardSummaryAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="boss",
            email="boss@example.com",
            password="testpass123",
            name="Admin",
            phone="9876500000",
            role="admin",
            is_staff=True,
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
        self.client.force_authenticate(user=self.admin)

    def _make_job(self, status, seq):
        return ServiceJob.objects.create(
            vehicle=self.vehicle,
            complaint="Engine noise",
            service_type="Full service",
            status=status,
            job_number=f"SJ-TEST-{seq}",
            created_by=self.admin,
        )

    def test_dashboard_summary_counts_and_recent_jobs(self):
        self._make_job("qc_pending", 1)
        self._make_job("in_progress", 2)
        self._make_job("delivered", 3)

        response = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        summary = response.data["data"]
        # active = everything except delivered/cancelled
        self.assertEqual(summary["active_jobs"], 2)
        self.assertEqual(summary["pending_qc"], 1)
        # recent jobs list must be present and contain the latest jobs
        self.assertIn("recent_jobs", summary)
        recent_ids = [job["id"] for job in summary["recent_jobs"]]
        expected_ids = list(self.vehicle.service_jobs.values_list("id", flat=True))
        self.assertEqual(set(recent_ids), set(expected_ids))
        self.assertEqual(len(recent_ids), 3)
        # every recent job exposes the fields the frontend JobCard needs
        recent = summary["recent_jobs"][0]
        for field in ("id", "job_number", "vehicle_number", "customer_name", "status"):
            self.assertIn(field, recent)

    def test_dashboard_summary_requires_admin(self):
        mechanic = User.objects.create_user(
            username="mechanic1",
            email="mechanic1@example.com",
            password="testpass123",
            name="Mechanic",
            phone="9876543211",
            role="mechanic",
        )
        self.client.force_authenticate(user=mechanic)
        response = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(response.status_code, 403)

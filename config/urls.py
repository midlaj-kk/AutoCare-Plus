from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from core.views import health_check

from apps.accounts.views import LoginView, MeView
from apps.accounts.urls import router as accounts_router
from apps.customers.views import CustomerViewSet
from apps.vehicles.views import VehicleViewSet
from apps.inventory.views import SparePartViewSet
from apps.service_jobs.views import ServiceJobViewSet
from apps.service_work.views import ServiceWorkViewSet
from apps.parts_used.views import PartUsedViewSet
from apps.quality_check.views import QualityCheckViewSet
from apps.billing.views import BillViewSet
from apps.payments.views import PaymentViewSet
from apps.delivery.views import DeliveryViewSet
from apps.mechanics.views import MechanicViewSet
from apps.service_history.views import VehicleHistoryView, CustomerHistoryView
from apps.dashboard.views import DashboardSummaryView
from apps.reports.views import (
    DailyRevenueReport, MonthlyRevenueReport,
    CompletedServicesReport, MechanicProductivityReport,
    SparePartsUsageReport,
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet)
router.register(r"vehicles", VehicleViewSet)
router.register(r"spare-parts", SparePartViewSet)
router.register(r"service-jobs", ServiceJobViewSet, basename="service-jobs")
router.register(r"works", ServiceWorkViewSet, basename="works")
router.register(r"parts-used", PartUsedViewSet, basename="parts-used")
router.register(r"quality-checks", QualityCheckViewSet)
router.register(r"bills", BillViewSet)
router.register(r"payments", PaymentViewSet)
router.register(r"delivery", DeliveryViewSet)
router.register(r"mechanics", MechanicViewSet)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("api/v1/auth/me/", MeView.as_view({"get": "list"}), name="me"),
    path("api/v1/", include(accounts_router.urls)),
    path("api/v1/", include(router.urls)),
    path("api/v1/vehicles/<int:vehicle_id>/history/", VehicleHistoryView.as_view(), name="vehicle-history"),
    path("api/v1/vehicles/history/", VehicleHistoryView.as_view(), name="vehicle-history-search"),
    path("api/v1/customers/<int:customer_id>/history/", CustomerHistoryView.as_view(), name="customer-history"),
    path("api/v1/dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("api/v1/reports/daily-revenue/", DailyRevenueReport.as_view(), name="daily-revenue"),
    path("api/v1/reports/monthly-revenue/", MonthlyRevenueReport.as_view(), name="monthly-revenue"),
    path("api/v1/reports/completed-services/", CompletedServicesReport.as_view(), name="completed-services"),
    path("api/v1/reports/mechanic-productivity/", MechanicProductivityReport.as_view(), name="mechanic-productivity"),
    path("api/v1/reports/spare-parts-usage/", SparePartsUsageReport.as_view(), name="spare-parts-usage"),
]

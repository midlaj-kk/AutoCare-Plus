from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from apps.service_jobs.models import ServiceJob
from apps.billing.models import Bill
from apps.inventory.models import SparePart


def get_admin_summary():
    today = timezone.now().date()
    return {
        "total_jobs_today": ServiceJob.objects.filter(created_at__date=today).count(),
        "active_jobs": ServiceJob.objects.exclude(
            status__in=["delivered", "cancelled"]
        ).count(),
        "pending_qc": ServiceJob.objects.filter(status="qc_pending").count(),
        "ready_for_delivery": ServiceJob.objects.filter(status="ready_for_delivery").count(),
        "revenue_today": Bill.objects.filter(created_at__date=today).aggregate(
            total=Sum("total_amount")
        )["total"] or 0,
        "low_stock_items": SparePart.objects.filter(
            stock_quantity__lte=F("minimum_stock"), status="active"
        ).count(),
    }

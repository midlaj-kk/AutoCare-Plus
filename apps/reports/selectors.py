from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.service_jobs.models import ServiceJob
from apps.billing.models import Bill
from apps.inventory.models import SparePart, StockMovement
from apps.accounts.models import User


def daily_revenue(date=None):
    if not date:
        date = timezone.now().date()
    return Bill.objects.filter(created_at__date=date).aggregate(
        total_revenue=Sum("total_amount"),
        total_bills=Count("id"),
    )


def monthly_revenue(month, year):
    return Bill.objects.filter(
        created_at__month=month, created_at__year=year
    ).aggregate(
        total_revenue=Sum("total_amount"),
        total_bills=Count("id"),
    )


def completed_services(from_date, to_date):
    return ServiceJob.objects.filter(
        status="delivered", updated_at__date__gte=from_date, updated_at__date__lte=to_date
    ).count()


def mechanic_productivity(from_date, to_date):
    return User.objects.filter(role="mechanic").annotate(
        jobs_completed=Count(
            "assigned_jobs",
            filter=Q(assigned_jobs__status="delivered")
            & Q(assigned_jobs__updated_at__date__gte=from_date)
            & Q(assigned_jobs__updated_at__date__lte=to_date),
        )
    ).values("id", "name", "jobs_completed")


def spare_parts_usage(from_date, to_date):
    from apps.parts_used.models import PartUsed
    return PartUsed.objects.filter(
        created_at__date__gte=from_date, created_at__date__lte=to_date
    ).values("part__name", "part__part_number").annotate(
        total_quantity=Sum("quantity")
    ).order_by("-total_quantity")

from .models import ServiceJob


def get_service_jobs(status=None, mechanic_id=None, vehicle_number=None):
    qs = ServiceJob.objects.select_related(
        "vehicle", "vehicle__customer", "assigned_mechanic", "created_by"
    ).prefetch_related("works", "parts_used", "parts_used__part")
    if status:
        qs = qs.filter(status=status)
    if mechanic_id:
        qs = qs.filter(assigned_mechanic_id=mechanic_id)
    if vehicle_number:
        qs = qs.filter(vehicle__vehicle_number__icontains=vehicle_number)
    return qs


def get_job_by_id(job_id):
    return ServiceJob.objects.select_related(
        "vehicle", "vehicle__customer", "assigned_mechanic", "created_by",
        "quality_check", "bill", "delivery",
    ).prefetch_related(
        "works", "parts_used", "parts_used__part", "bill__payments",
    ).filter(id=job_id).first()


def get_jobs_for_mechanic(mechanic_id):
    return ServiceJob.objects.filter(assigned_mechanic_id=mechanic_id).select_related(
        "vehicle", "vehicle__customer"
    )

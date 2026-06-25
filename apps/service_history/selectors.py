from apps.service_jobs.models import ServiceJob


def get_vehicle_history(vehicle_id):
    return ServiceJob.objects.filter(vehicle_id=vehicle_id).select_related(
        "assigned_mechanic", "bill"
    ).prefetch_related("works", "parts_used__part")


def get_vehicle_history_by_number(vehicle_number):
    return ServiceJob.objects.filter(
        vehicle__vehicle_number__iexact=vehicle_number
    ).select_related(
        "assigned_mechanic", "bill", "vehicle"
    ).prefetch_related("works", "parts_used__part")


def get_customer_history(customer_id):
    return ServiceJob.objects.filter(
        vehicle__customer_id=customer_id
    ).select_related("vehicle", "assigned_mechanic", "bill").prefetch_related(
        "works", "parts_used__part"
    )

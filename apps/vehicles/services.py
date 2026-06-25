from core.services import safe_deactivate_or_block
from apps.service_jobs.models import ServiceJob
from core.utils import normalize_vehicle_number


def create_vehicle(data):
    from .models import Vehicle
    data["vehicle_number"] = normalize_vehicle_number(data["vehicle_number"])
    return Vehicle.objects.create(**data)


def update_vehicle(vehicle, data):
    if "vehicle_number" in data:
        data["vehicle_number"] = normalize_vehicle_number(data["vehicle_number"])
    for field, value in data.items():
        setattr(vehicle, field, value)
    vehicle.save()
    return vehicle


def delete_vehicle(vehicle):
    return safe_deactivate_or_block(vehicle, {
        "service_jobs": ServiceJob.objects.filter(vehicle=vehicle),
    })

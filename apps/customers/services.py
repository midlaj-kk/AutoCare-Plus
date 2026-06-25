from core.services import safe_deactivate_or_block
from apps.vehicles.models import Vehicle
from apps.service_jobs.models import ServiceJob


def create_customer(data):
    from .models import Customer
    return Customer.objects.create(**data)


def update_customer(customer, data):
    for field, value in data.items():
        setattr(customer, field, value)
    customer.save()
    return customer


def delete_customer(customer):
    return safe_deactivate_or_block(customer, {
        "vehicles": Vehicle.objects.filter(customer=customer),
        "service_jobs": ServiceJob.objects.filter(vehicle__customer=customer),
    })

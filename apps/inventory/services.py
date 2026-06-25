from django.db import transaction
from .models import SparePart, StockMovement


class InsufficientStockError(Exception):
    pass


def create_spare_part(data):
    return SparePart.objects.create(**data)


def update_spare_part(part, data):
    for field, value in data.items():
        setattr(part, field, value)
    part.save()
    return part


@transaction.atomic
def add_stock(part_id, quantity, reference_type, reference_id, actor):
    part = SparePart.objects.select_for_update().get(id=part_id)
    part.stock_quantity += quantity
    part.save(update_fields=["stock_quantity"])

    StockMovement.objects.create(
        spare_part=part,
        movement_type="in",
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=actor,
    )
    return part


@transaction.atomic
def reduce_stock(part_id, quantity, reason, actor):
    part = SparePart.objects.select_for_update().get(id=part_id)
    if part.stock_quantity < quantity:
        raise InsufficientStockError(
            f"Only {part.stock_quantity} {part.unit} of {part.name} available."
        )
    part.stock_quantity -= quantity
    part.save(update_fields=["stock_quantity"])

    StockMovement.objects.create(
        spare_part=part,
        movement_type="out",
        quantity=quantity,
        reference_type="adjustment",
        reference_id=None,
        created_by=actor,
    )
    return part


@transaction.atomic
def consume_part(service_job, spare_part_id, quantity, actor):
    part = SparePart.objects.select_for_update().get(id=spare_part_id)
    if part.stock_quantity < quantity:
        raise InsufficientStockError(
            f"Only {part.stock_quantity} {part.unit} of {part.name} available."
        )
    part.stock_quantity -= quantity
    part.save(update_fields=["stock_quantity"])

    StockMovement.objects.create(
        spare_part=part,
        movement_type="out",
        quantity=quantity,
        reference_type="service_job",
        reference_id=service_job.id,
        created_by=actor,
    )
    from apps.parts_used.models import PartUsed
    return PartUsed.objects.create(
        service_job=service_job,
        part=part,
        quantity=quantity,
        price=part.selling_price,
        added_by=actor,
    )


@transaction.atomic
def restore_part(part_used, actor):
    part = SparePart.objects.select_for_update().get(id=part_used.part_id)
    part.stock_quantity += part_used.quantity
    part.save(update_fields=["stock_quantity"])

    StockMovement.objects.create(
        spare_part=part,
        movement_type="in",
        quantity=part_used.quantity,
        reference_type="adjustment",
        reference_id=part_used.service_job_id,
        created_by=actor,
    )
    part_used.delete()

from django.db import transaction
from django.utils import timezone


class HasActiveDependentsError(Exception):
    def __init__(self, model_name, count):
        self.model_name = model_name
        self.count = count
        super().__init__(
            f"{model_name} has {count} dependent record(s); deactivating instead of deleting."
        )


def safe_deactivate_or_block(instance, dependent_querysets):
    for name, qs in dependent_querysets.items():
        if qs.exists():
            instance.status = "inactive"
            instance.save(update_fields=["status"])
            return "deactivated", instance
    instance.delete()
    return "deleted", instance


def generate_sequential_code(prefix, model, field_name="job_number"):
    from django.apps import apps
    SequenceCounter = apps.get_model("core", "SequenceCounter")

    year = timezone.now().year
    with transaction.atomic():
        seq, _ = SequenceCounter.objects.select_for_update().get_or_create(
            prefix=prefix, year=year, defaults={"last_value": 0}
        )
        seq.last_value += 1
        seq.save(update_fields=["last_value"])
        return f"{prefix}-{year}-{seq.last_value:05d}"

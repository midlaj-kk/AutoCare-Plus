import re
from django.core.exceptions import ValidationError


def validate_phone(value):
    pattern = r"^\+?[0-9]{10,15}$"
    if not re.match(pattern, value):
        raise ValidationError(
            f"{value} is not a valid phone number. Must be 10-15 digits."
        )


def validate_vehicle_number(value):
    normalized = value.upper().strip()
    if len(normalized) < 3:
        raise ValidationError("Vehicle number is too short.")
    return normalized

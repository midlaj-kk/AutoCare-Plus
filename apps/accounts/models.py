from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SERVICE_ADVISOR = "service_advisor", "Service Advisor"
        MECHANIC = "mechanic", "Mechanic"
        CASHIER = "cashier", "Cashier"

    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=20, choices=Role.choices)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

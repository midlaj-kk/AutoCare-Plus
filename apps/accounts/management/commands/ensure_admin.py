from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decouple import config

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a default admin superuser if none exists"

    def handle(self, *args, **options):
        if User.objects.filter(role="admin").exists():
            self.stdout.write("Admin user already exists, skipping.")
            return

        email = config("ADMIN_EMAIL", default="admin@autocare.com")
        password = config("ADMIN_PASSWORD", default="admin123")
        name = config("ADMIN_NAME", default="Admin")

        User.objects.create_superuser(
            username=email,
            email=email,
            name=name,
            phone="0000000000",
            role="admin",
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Default admin created: {email}"))

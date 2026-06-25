import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.utils import ProgrammingError, OperationalError
from decouple import config

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a default admin superuser if none exists"

    def handle(self, *args, **options):
        try:
            if User.objects.filter(role="admin").exists():
                self.stdout.write("Admin user already exists, skipping.")
                return
        except (ProgrammingError, OperationalError) as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Database table not ready yet ({e}). Skipping admin creation."
                )
            )
            return

        email = config("ADMIN_EMAIL", default="admin@autocare.com")
        password = config("ADMIN_PASSWORD", default="admin123")
        name = config("ADMIN_NAME", default="Admin")

        self.stdout.write(
            f"Creating admin: email={email}, name={name}, password={'***' if password else 'EMPTY'}"
        )

        try:
            User.objects.create_superuser(
                username=email,
                email=email,
                name=name,
                phone="0000000000",
                role="admin",
                password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Default admin created: {email}"))
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Failed to create admin user: {e}")
            )
            sys.exit(1)

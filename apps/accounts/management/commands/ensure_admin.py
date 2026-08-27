import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.utils import ProgrammingError, OperationalError
from decouple import config

User = get_user_model()


class Command(BaseCommand):
    help = "Ensures a staff superuser admin exists"

    def handle(self, *args, **options):
        email = config("ADMIN_EMAIL", default="admin@autocare.com")
        password = config("ADMIN_PASSWORD", default="admin123")
        name = config("ADMIN_NAME", default="Admin")

        # 1. If a real superuser already exists, nothing to do.
        try:
            if User.objects.filter(is_superuser=True).exists():
                self.stdout.write("Superuser already exists, skipping.")
                return
        except (ProgrammingError, OperationalError) as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Database table not ready yet ({e}). Skipping admin creation."
                )
            )
            return

        # 2. If a role="admin" user exists but isn't a superuser, promote it.
        try:
            existing_admin = User.objects.filter(role="admin").first()
            if existing_admin:
                existing_admin.is_staff = True
                existing_admin.is_superuser = True
                existing_admin.is_active = True
                existing_admin.status = "active"
                existing_admin.email = existing_admin.email or email
                existing_admin.username = existing_admin.username or existing_admin.email
                existing_admin.set_password(password)
                existing_admin.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Promoted existing admin to superuser: {existing_admin.email}")
                )
                return
        except (ProgrammingError, OperationalError) as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Database table not ready yet ({e}). Skipping admin creation."
                )
            )
            return

        # 3. Otherwise create a brand new superuser.
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
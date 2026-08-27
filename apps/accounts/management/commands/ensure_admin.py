import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.utils import ProgrammingError, OperationalError, IntegrityError
from decouple import config

User = get_user_model()


class Command(BaseCommand):
    help = "Ensures the configured admin superuser exists with the configured email/password"

    def handle(self, *args, **options):
        email = config("ADMIN_EMAIL", default="admin@autocare.com")
        password = config("ADMIN_PASSWORD", default="admin@123")
        name = config("ADMIN_NAME", default="Admin")

        try:
            admin = User.objects.filter(email__iexact=email).first()
            if admin:
                self._promote(admin, email, password, name, "Admin found by email")
                return

            existing = (
                User.objects.filter(role="admin")
                .order_by("is_superuser", "id")
                .first()
            )
            if existing:
                self._promote(existing, email, password, name, "Promoted existing admin")
                return

            superuser = User.objects.filter(is_superuser=True).first()
            if superuser:
                self._promote(superuser, email, password, name, "Promoted existing superuser")
                return

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
                    status="active",
                    password=password,
                )
                self.stdout.write(self.style.SUCCESS(f"Default admin created: {email}"))
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Failed to create admin user: {e}")
                )
                sys.exit(1)
        except (ProgrammingError, OperationalError) as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Database table not ready yet ({e}). Skipping admin creation."
                )
            )
            return

    def _promote(self, user, email, password, name, message):
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.status = "active"
        user.role = user.role or "admin"
        user.email = email
        user.username = user.username or email
        user.name = user.name or name
        user.set_password(password)
        try:
            user.save()
        except IntegrityError as e:
            self.stderr.write(
                self.style.ERROR(
                    f"Could not set email {email!r} on {user} (already in use by another user): {e}"
                )
            )
            return
        self.stdout.write(self.style.SUCCESS(f"{message}: {user.email}"))
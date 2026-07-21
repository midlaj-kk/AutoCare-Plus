from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "name", "role", "status", "is_active")
    list_filter = ("role", "status", "is_active")
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal Info", {"fields": ("name", "phone", "specialization")}),
        ("Permissions", {"fields": ("role", "status", "is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "name", "phone", "password1", "password2", "role"),
        }),
    )
    search_fields = ("email", "name", "phone")
    ordering = ("email",)

    def save_model(self, request, obj, form, change):
        if not change and not obj.username:
            obj.username = obj.email
        super().save_model(request, obj, form, change)

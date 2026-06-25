from django.contrib.auth import get_user_model

User = get_user_model()


def create_user(name, email, phone, role, password, specialization=None):
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        name=name,
        phone=phone,
        role=role,
        specialization=specialization,
    )
    return user


def update_user(user, data):
    for field, value in data.items():
        if field != "password":
            setattr(user, field, value)
    if "password" in data and data["password"]:
        user.set_password(data["password"])
    user.save()
    return user


def deactivate_user(user):
    user.status = "inactive"
    user.is_active = False
    user.save(update_fields=["status", "is_active"])
    return user


def activate_user(user):
    user.status = "active"
    user.is_active = True
    user.save(update_fields=["status", "is_active"])
    return user

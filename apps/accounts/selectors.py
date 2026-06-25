from django.contrib.auth import get_user_model

User = get_user_model()


def get_users(role=None, status=None):
    qs = User.objects.all()
    if role:
        qs = qs.filter(role=role)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_mechanics():
    return User.objects.filter(role="mechanic", status="active")


def get_user_by_id(user_id):
    return User.objects.filter(id=user_id).first()

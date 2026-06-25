from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    ChangePasswordSerializer,
)
from core.permissions import IsAdmin
from .services import create_user, update_user, deactivate_user, activate_user
from .selectors import get_users


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["patch"])
    def activate(self, request, pk=None):
        user = self.get_object()
        activate_user(user)
        return Response({"success": True, "message": "User activated."})

    @action(detail=True, methods=["patch"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        deactivate_user(user)
        return Response({"success": True, "message": "User deactivated."})


class MeView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        serializer = UserSerializer(request.user)
        return Response({"success": True, "message": "Profile fetched", "data": serializer.data})

from django.db.models import Q
from django.utils import timezone
from .serializer import UserSerializer, AdminUserSerializer
from .models import User
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .permisions import IsOwnerOrAdmin, IsAdminOrSuperAdmin

# Create your views here.

class UserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserSerializer
        user = self.request.user
        if user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "superadmin")
        ):
            return AdminUserSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        role = self.request.query_params.get("role")
        status = self.request.query_params.get("status")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        if role:
            qs = qs.filter(role=role)
        if status:
            qs = qs.filter(status=status)
        return qs

    def perform_update(self, serializer):
        serializer.save(last_active=timezone.now())

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [AllowAny]
        elif self.action in ("update", "partial_update", "destroy"):
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        elif self.action == "set_status":
            permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [
            permission()
            for permission in permission_classes
        ]

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Non authentifié."}, status=401)
        if request.method == "PATCH":
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(request.user).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        user = self.get_object()
        user.status = request.data.get("status", user.status)
        if user.status == User.AccountStatus.SUSPENDED:
            user.is_active = False
        elif user.status == User.AccountStatus.ACTIVE:
            user.is_active = True
        user.save()
        return Response(AdminUserSerializer(user).data)
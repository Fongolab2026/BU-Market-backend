from django.shortcuts import render
from .serializer import UserSerializer
from .models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permisions import IsOwnerOrAdmin

# Create your views here.

class UserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [AllowAny]
        elif self.action in ("update", "partial_update", "destroy"):
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [
            permission()
            for permission in permission_classes
        ]
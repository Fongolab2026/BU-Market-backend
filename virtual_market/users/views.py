from django.db.models import Q
from django.utils import timezone
from .serializer import UserSerializer, AdminUserSerializer
from .models import User
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
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

    def _is_admin(self, user):
        return user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "superadmin")
        )

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # Un utilisateur non-admin ne peut cibler que son propre compte : la
        # liste complete est reservee a l'administration.
        if not self._is_admin(user):
            qs = qs.filter(pk=user.pk) if user.is_authenticated else qs.none()
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
        elif self.action == "list":
            permission_classes = [IsAdminOrSuperAdmin]
        elif self.action in ("retrieve", "update", "partial_update", "destroy"):
            # Soi-meme ou un administrateur uniquement (verifie sur l'objet).
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        elif self.action == "set_status":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            # me
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

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """Change le mot de passe de l'utilisateur connecté.

        Exige le mot de passe actuel (preuve de possession du compte).
        """
        current = request.data.get("current_password") or request.data.get("current")
        new = request.data.get("new_password") or request.data.get("password")

        if not current or not new:
            return Response(
                {"detail": "Le mot de passe actuel et le nouveau mot de passe sont requis."},
                status=400,
            )
        if not request.user.check_password(current):
            return Response(
                {"current_password": ["Le mot de passe actuel est incorrect."]},
                status=400,
            )
        if len(new) < 8:
            return Response(
                {"new_password": ["Le nouveau mot de passe doit contenir au moins 8 caractères."]},
                status=400,
            )
        if new == current:
            return Response(
                {"new_password": ["Le nouveau mot de passe doit être différent de l'actuel."]},
                status=400,
            )

        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Mot de passe mis à jour avec succès."})

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


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Connexion par adresse e-mail uniquement.

    Le nom d'utilisateur n'est plus accepté : on évite ainsi qu'un même
    identifiant puisse ouvrir deux comptes de rôles différents.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On remplace le champ « username » par un champ « email ».
        self.fields.pop(self.username_field, None)
        self.fields["email"] = serializers.EmailField(
            error_messages={
                "required": "L'adresse e-mail est requise.",
                "invalid": "Adresse e-mail invalide.",
            }
        )

    def validate(self, attrs):
        # SimpleJWT attend une valeur dans « username_field » : on lui
        # transmet l'e-mail saisi.
        attrs[self.username_field] = attrs.get("email")
        try:
            return super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed("E-mail ou mot de passe incorrect.")


class EmailTokenObtainPairView(TokenObtainPairView):
    """Vue de connexion par adresse e-mail."""

    serializer_class = EmailTokenObtainPairSerializer
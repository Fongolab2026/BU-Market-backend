from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


#: Libelles de l'interface admin -> valeurs reelles stockees en base.
ADMIN_ROLE_TO_MODEL = {
    "merchant": User.Role.SELLER,
    "seller": User.Role.SELLER,
    "client": User.Role.BUYER,
    "buyer": User.Role.BUYER,
    "admin": User.Role.ADMIN,
    "superadmin": User.Role.SUPER_ADMIN,
}


def normalize_admin_role(value):
    """Accepte les libelles de l'interface admin et renvoie la valeur du modele."""
    if not value:
        return None
    return ADMIN_ROLE_TO_MODEL.get(str(value).strip().lower())


def build_username(email, first_name=""):
    """Fabrique un identifiant unique a partir de l'e-mail et du prenom."""
    base = (str(email or "").split("@")[0] or "user").strip().lower()
    base = "".join(char for char in base if char.isalnum() or char in "._-") or "user"
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.RegexField(
        regex=r'^\+?\d{8,15}$',
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "phone",
            "adresse",
            "profile_pic",
            "role",
            "is_active",
            "password",
        ]
        read_only_fields = ["role", "is_active"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

    def to_internal_value(self, data):
        """Accepte les libelles de role de l'interface admin (merchant, client...)."""
        mutable = data.copy()
        if "role" in mutable:
            mutable["role"] = normalize_admin_role(mutable.get("role")) or mutable["role"]
        if mutable.get("location"):
            mutable["adresse"] = mutable["location"]
        mutable.pop("location", None)
        return super().to_internal_value(mutable)


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Creation d'un compte depuis l'interface admin.

    Le formulaire n'envoie que prenom / e-mail / telephone / localisation / role :
    l'identifiant et le mot de passe sont generes cote serveur.
    """

    firstName = serializers.CharField(source="first_name", max_length=150)
    location = serializers.CharField(source="adresse", required=False, allow_blank=True)
    role = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "firstName", "email", "phone", "location", "role", "password"]
        read_only_fields = ["id", "username"]

    def validate_email(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("L'e-mail est obligatoire.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte utilise deja cet e-mail.")
        return value

    def validate_role(self, value):
        role = normalize_admin_role(value)
        if role is None:
            raise serializers.ValidationError("Role inconnu.")
        return role

    def create(self, validated_data):
        password = validated_data.pop("password", "") or build_username(
            validated_data.get("email")
        ) + "1!"
        user = User(username=build_username(validated_data.get("email")), **validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer « camelCase » consommé par l'interface admin."""

    id = serializers.IntegerField(read_only=True)
    firstName = serializers.CharField(source="first_name")
    joinedAt = serializers.DateTimeField(source="date_joined", read_only=True)
    lastActive = serializers.DateTimeField(source="last_active", read_only=True)
    location = serializers.CharField(source="adresse", required=False, allow_blank=True)
    shop = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "firstName",
            "email",
            "phone",
            "role",
            "status",
            "is_active",
            "joinedAt",
            "lastActive",
            "location",
            "shop",
            "timeline",
            "password",
        ]
        read_only_fields = ["is_active"]

    def get_shop(self, obj):
        if not obj.is_seller:
            return None
        return {
            "id": obj.id,
            "name": obj.shop_display_name,
            "status": obj.shop_status,
        }

    def get_timeline(self, obj):
        entries = []

        for order in obj.orders.all()[:3]:
            entries.append(
                {
                    "id": f"order-{order.id}",
                    "label": f"Commande #{order.id} ({order.get_status_display()})",
                    "date": order.created_at.isoformat(),
                    "kind": "order",
                }
            )

        for notif in obj.notifications.all()[:3]:
            entries.append(
                {
                    "id": f"notification-{notif.id}",
                    "label": notif.title,
                    "date": notif.created_at.isoformat(),
                    "kind": "notification",
                }
            )

        for product in obj.products.all()[:3]:
            entries.append(
                {
                    "id": f"product-{product.id}",
                    "label": f"Produit créé : {product.name}",
                    "date": product.created_at.isoformat(),
                    "kind": "product",
                }
            )

        entries.sort(key=lambda entry: entry["date"], reverse=True)
        return entries[:10]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Le mot de passe est requis."})
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
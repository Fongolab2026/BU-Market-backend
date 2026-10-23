from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "L'adresse e-mail est obligatoire.",
            "blank": "L'adresse e-mail est obligatoire.",
            "invalid": "Adresse e-mail invalide.",
        },
    )
    phone = serializers.RegexField(
        regex=r'^\+?\d{8,15}$',
        required=False,
        allow_blank=True,
        validators=[],
    )
    # Accepte les noms de champs camelCase du front admin
    firstName = serializers.CharField(source="first_name", required=False, allow_blank=True)
    lastName = serializers.CharField(source="last_name", required=False, allow_blank=True)
    location = serializers.CharField(source="adresse", required=False, allow_blank=True)
    is_seller = serializers.BooleanField(read_only=True)
    shop = serializers.SerializerMethodField()
    shop_name = serializers.CharField(required=False, allow_blank=True)
    shop_description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "firstName",
            "lastName",
            "phone",
            "adresse",
            "location",
            "profile_pic",
            "role",
            "is_active",
            "is_seller",
            "shop",
            "shop_name",
            "shop_description",
            "password",
        ]
        read_only_fields = ["role", "is_active"]

    def get_shop(self, obj):
        """Résumé de la boutique, utilisé par l'espace vendeur côté frontend."""
        if not obj.is_seller and not obj.shop_name:
            return None
        return {
            "id": obj.id,
            "name": obj.shop_display_name,
            "status": obj.shop_status,
        }

    def validate_email(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("L'adresse e-mail est obligatoire.")
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return value

    def validate_phone(self, value):
        value = (value or "").strip()
        if not value:
            return value
        qs = User.objects.filter(phone=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Le mot de passe est requis."})
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        # Le mot de passe ne se modifie pas via la mise à jour générique :
        # il faut passer par l'action « change-password » qui vérifie l'actuel.
        if validated_data.pop("password", None):
            raise serializers.ValidationError(
                {"password": "Utilisez la fonction « Changer le mot de passe »."}
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer « camelCase » consommé par l'interface admin."""

    id = serializers.IntegerField(read_only=True)
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    joinedAt = serializers.DateTimeField(source="date_joined", read_only=True)
    lastActive = serializers.DateTimeField(source="last_active", read_only=True)
    location = serializers.CharField(source="adresse", required=False, allow_blank=True)
    shop = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    profilePic = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)
    phone = serializers.CharField(required=False, allow_blank=True, validators=[])
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "L'adresse e-mail est obligatoire.",
            "blank": "L'adresse e-mail est obligatoire.",
            "invalid": "Adresse e-mail invalide.",
        },
    )
    # Accepte les rôles « buyer » / « merchant » côté front et les convertit en « buyer » / « seller ».
    role = serializers.ChoiceField(
        choices=["buyer", "merchant", "seller", "admin", "superadmin"],
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "firstName",
            "lastName",
            "email",
            "phone",
            "role",
            "status",
            "is_active",
            "joinedAt",
            "lastActive",
            "location",
            "profilePic",
            "shop",
            "timeline",
            "password",
        ]
        read_only_fields = ["is_active"]

    def get_profilePic(self, obj):
        if not obj.profile_pic:
            return None
        request = self.context.get("request")
        url = obj.profile_pic.url
        return request.build_absolute_uri(url) if request is not None else url

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

    def validate_email(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("L'adresse e-mail est obligatoire.")
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return value

    def validate_phone(self, value):
        value = (value or "").strip()
        if not value:
            return value
        qs = User.objects.filter(phone=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return value

    def validate_role(self, value):
        """Convertit les rôles front (buyer/merchant) en rôles back (buyer/seller)."""
        role_map = {
            "buyer": User.Role.BUYER,
            "merchant": User.Role.SELLER,
            "seller": User.Role.SELLER,
            "admin": User.Role.ADMIN,
            "superadmin": User.Role.SUPER_ADMIN,
        }
        return role_map.get(value, value)

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
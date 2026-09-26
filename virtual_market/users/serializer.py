from rest_framework import serializers
from .models import User


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
from rest_framework import serializers
from .models import Favorite


class FavoriteSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Favorite
        fields = [
            "id",
            "user",
            "user_username",
            "product",
            "product_name",
            "stars",
            "created_at",
        ]
        read_only_fields = ["user"]

    def validate_stars(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Les étoiles doivent être comprises entre 1 et 5.")
        return value
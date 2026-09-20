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
            "comment",
            "created_at",
        ]
        read_only_fields = ["user"]

    def validate_stars(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Les étoiles doivent être comprises entre 1 et 5.")
        return value


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="user.username", read_only=True)
    note = serializers.IntegerField(source="stars", read_only=True)
    comment = serializers.CharField(read_only=True)
    date = serializers.DateTimeField(source="created_at", read_only=True)
    shopId = serializers.IntegerField(source="product.owner_id", read_only=True)
    shopName = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = [
            "id",
            "product",
            "author",
            "note",
            "comment",
            "date",
            "status",
            "shopId",
            "shopName",
        ]
        read_only_fields = ["status"]

    def get_shopName(self, obj):
        return obj.product.owner.shop_display_name
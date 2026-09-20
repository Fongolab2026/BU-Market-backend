from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source="created_at", read_only=True)
    shopId = serializers.IntegerField(source="owner_id", read_only=True)
    shopName = serializers.SerializerMethodField()
    shopCategory = serializers.SerializerMethodField()
    shopStatus = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "stock",
            "status",
            "views",
            "details",
            "category",
            "owner",
            "created_at",
            "date",
            "shopId",
            "shopName",
            "shopCategory",
            "shopStatus",
        ]
        read_only_fields = ["owner", "views", "status"]

    def get_shopName(self, obj):
        return obj.owner.shop_display_name

    def get_shopCategory(self, obj):
        return obj.owner.shop_category.name if obj.owner.shop_category else ""

    def get_shopStatus(self, obj):
        return obj.owner.shop_status
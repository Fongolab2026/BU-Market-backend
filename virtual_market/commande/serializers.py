from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "order", "product", "product_name", "quantity", "price", "subtotal"]

    def get_subtotal(self, obj):
        return obj.subtotal


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    client = serializers.CharField(source="user.username", read_only=True)
    location = serializers.CharField(source="user.adresse", read_only=True, default="")
    shop = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "client",
            "location",
            "shop",
            "admin",
            "server",
            "status",
            "items",
            "total_price",
            "date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user"]

    def get_total_price(self, obj):
        return obj.total_price

    def get_shop(self, obj):
        first_item = obj.items.select_related("product__owner").first()
        if first_item:
            return first_item.product.owner.shop_display_name
        return ""
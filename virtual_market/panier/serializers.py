from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "cart", "product", "product_name", "quantity", "subtotal", "added_at"]

    def get_subtotal(self, obj):
        return obj.subtotal


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_prices = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total_prices", "created_at", "updated_at"]

    def get_total_prices(self, obj):
        return obj.total_prices
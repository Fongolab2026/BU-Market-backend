from django.core.files.storage import default_storage
from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "order", "product", "product_name", "quantity", "price", "subtotal"]

    def get_subtotal(self, obj):
        return obj.subtotal


class ShopOrderItemSerializer(serializers.ModelSerializer):
    """Article de commande pour la vue vendeur (shop-orders)."""
    product_name = serializers.CharField(read_only=True)
    subtotal = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "price", "subtotal", "product_image"]

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_product_image(self, obj):
        request = self.context.get("request")
        url = None
        if obj.product_id:
            images = list(obj.product.images.all())
            main = next((img for img in images if img.is_main), None) or (images[0] if images else None)
            if main and main.image:
                url = main.image.url
        if not url and obj.product_image_key:
            url = default_storage.url(obj.product_image_key)
        return request.build_absolute_uri(url) if request and url else url


class ShopOrderSerializer(serializers.Serializer):
    """Sérialiseur pour les commandes du vendeur (shop-orders)."""
    id = serializers.IntegerField()
    client = serializers.CharField(source="order.user.username")
    location = serializers.CharField(source="order.user.adresse", default="")
    status = serializers.CharField(source="order.status")
    date = serializers.DateTimeField(source="order.created_at")
    items = ShopOrderItemSerializer(many=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, source="total")
    can_update_status = serializers.SerializerMethodField()

    def get_can_update_status(self, obj):
        return obj.get("seller_ids") == {obj["items"][0].seller_id}


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
        shops = obj.items.exclude(shop_name="").values_list("shop_name", flat=True).distinct()
        shop_list = list(shops)
        if len(shop_list) == 1:
            return shop_list[0]
        elif len(shop_list) > 1:
            return f"{shop_list[0]} + {len(shop_list) - 1} autre(s)"
        return ""

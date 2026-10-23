from rest_framework import serializers
from products.models import Product
from .models import Cart, CartItem


class AddToCartSerializer(serializers.Serializer):
    """Entrée de l'action `add-item` : produit + quantité à ajouter."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.SerializerMethodField()
    # Stock restant du produit : permet au front d'empêcher de dépasser la quantité disponible.
    stock = serializers.IntegerField(source="product.stock", read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "cart",
            "product",
            "product_name",
            "quantity",
            "subtotal",
            "stock",
            "added_at",
        ]
        # An item can only change quantity through its own cart. Allowing a
        # client to move it to another cart or swap its product breaks cart
        # ownership and stock checks.
        read_only_fields = ["cart", "added_at"]

    def get_fields(self):
        fields = super().get_fields()
        # Product can be selected when creating an item, but cannot be swapped
        # after creation; quantity changes must stay tied to the same SKU.
        if self.instance is not None:
            fields["product"].read_only = True
        return fields

    def get_subtotal(self, obj):
        return obj.subtotal

    def validate(self, attrs):
        product = attrs.get("product") or getattr(self.instance, "product", None)
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 1))
        if quantity is not None and quantity < 1:
            raise serializers.ValidationError(
                {"quantity": "La quantité doit être au moins 1."}
            )
        if product is not None and quantity is not None and quantity > product.stock:
            raise serializers.ValidationError(
                {"quantity": f"Stock insuffisant. Disponible : {product.stock}."}
            )
        if product is not None and product.status != Product.Status.ACTIVE:
            raise serializers.ValidationError(
                {"product": "Ce produit n'est plus disponible."}
            )
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_prices = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total_prices", "created_at", "updated_at"]
        read_only_fields = ["user"]

    def get_total_prices(self, obj):
        return obj.total_prices

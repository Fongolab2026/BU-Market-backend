from rest_framework import serializers
from products.models import Product
from .models import PublicationRequest


class PublicationRequestSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        write_only=True,
    )
    product = serializers.SerializerMethodField()
    seller = serializers.CharField(source="seller.username", read_only=True)
    shop = serializers.CharField(source="seller.shop_display_name", read_only=True)
    date = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = PublicationRequest
        fields = [
            "id",
            "product_id",
            "product",
            "seller",
            "shop",
            "date",
            "status",
            "created_at",
        ]
        read_only_fields = ["status", "seller"]

    def get_product(self, obj):
        return {
            "id": obj.product.id,
            "name": obj.product.name,
            "category": obj.product.category.name,
            "price": obj.product.price,
        }
from rest_framework import serializers
from categorie.models import Category
from .models import Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_main"]

    def get_image(self, obj):
        request = self.context.get("request")
        url = obj.image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    main_image = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at", read_only=True)
    shopId = serializers.IntegerField(source="owner_id", read_only=True)
    shopName = serializers.SerializerMethodField()
    shopCategory = serializers.SerializerMethodField()
    shopStatus = serializers.SerializerMethodField()
    details = serializers.CharField(required=False, allow_blank=True, default="")
    name = serializers.CharField(max_length=100, error_messages={"blank": "Le nom du produit est obligatoire."})
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        error_messages={"required": "Le prix est obligatoire.", "invalid": "Le prix doit être un nombre."},
    )
    stock = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        error_messages={"invalid": "Le stock doit être un entier.", "min_value": "Le stock ne peut pas être négatif."},
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        error_messages={
            "required": "La catégorie est obligatoire.",
            "does_not_exist": "Cette catégorie n'existe pas.",
            "incorrect_type": "Catégorie invalide.",
        },
    )

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
            "images",
            "main_image",
        ]
        read_only_fields = ["owner", "views", "status"]

    def get_main_image(self, obj):
        request = self.context.get("request")
        images = obj.images.all()
        main = next((img for img in images if img.is_main), None) or images[0] if images else None
        url = main.image.url if main else None
        if url and request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_shopName(self, obj):
        return obj.owner.shop_display_name

    def get_shopCategory(self, obj):
        return obj.owner.shop_category.name if obj.owner.shop_category else ""

    def get_shopStatus(self, obj):
        return obj.owner.shop_status
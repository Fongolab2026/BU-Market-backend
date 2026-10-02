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
    categoryName = serializers.SerializerMethodField()
    sellerName = serializers.SerializerMethodField()
    sellerEmail = serializers.SerializerMethodField()
    sellerPhone = serializers.SerializerMethodField()
    sellerAddress = serializers.SerializerMethodField()
    sellerWebsite = serializers.SerializerMethodField()
    sellerFacebook = serializers.SerializerMethodField()
    sellerInstagram = serializers.SerializerMethodField()
    sellerTiktok = serializers.SerializerMethodField()

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
            "categoryName",
            "sellerName",
            "sellerEmail",
            "sellerPhone",
            "sellerAddress",
            "sellerWebsite",
            "sellerFacebook",
            "sellerInstagram",
            "sellerTiktok",
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
        extra_kwargs = {
            "details": {"required": False, "allow_blank": True},
        }

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

    def get_categoryName(self, obj):
        return obj.category.name

    def get_shopCategory(self, obj):
        return obj.owner.shop_category.name if obj.owner.shop_category else ""

    def get_shopStatus(self, obj):
        return obj.owner.shop_status

    def _validated_boutique(self, obj):
        from shops.models import Boutique

        return obj.owner.boutiques.filter(status=Boutique.Status.VALIDATED).order_by("-created_at").first()

    def get_sellerName(self, obj):
        name = " ".join(
            part.strip()
            for part in (obj.owner.first_name, getattr(obj.owner, "last_name", ""))
            if part and str(part).strip()
        )
        return name or obj.owner.username

    def get_sellerEmail(self, obj):
        return obj.owner.email

    def get_sellerPhone(self, obj):
        return obj.owner.phone

    def get_sellerAddress(self, obj):
        return obj.owner.adresse

    def get_sellerWebsite(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.website if boutique else ""

    def get_sellerFacebook(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.facebook if boutique else ""

    def get_sellerInstagram(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.instagram if boutique else ""

    def get_sellerTiktok(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.tiktok if boutique else ""


class AdminProductWriteSerializer(serializers.ModelSerializer):
    """Ecriture produit depuis l'interface admin.

    Le formulaire admin envoie `shopId` (le proprietaire) ; la categorie est
    obligatoire uniquement a la creation et la description reste facultative.
    """

    shopId = serializers.IntegerField(required=False, write_only=True)
    categoryId = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "shopId",
            "categoryId",
            "name",
            "price",
            "stock",
            "details",
            "status",
        ]
        extra_kwargs = {"details": {"required": False, "allow_blank": True}}

    def validate(self, attrs):
        category_id = attrs.pop("categoryId", None)
        attrs.pop("shopId", None)
        if category_id:
            try:
                attrs["category"] = Category.objects.get(pk=category_id)
            except (Category.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError(
                    {"categoryId": "Categorie introuvable."}
                )
        elif self.instance is None:
            raise serializers.ValidationError(
                {"categoryId": "Choisissez une categorie pour le produit."}
            )
        attrs.setdefault("details", "")
        return attrs

    def to_representation(self, instance):
        return ProductSerializer(instance, context=self.context).data
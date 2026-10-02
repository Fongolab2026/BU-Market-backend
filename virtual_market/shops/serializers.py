from rest_framework import serializers

from users.models import User
from products.models import Product
from products.serializers import ProductSerializer
from favoris.serializers import ReviewSerializer
from .models import Boutique


class ShopSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    status = serializers.CharField(source="shop_status", read_only=True)
    rating = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="date_joined", read_only=True)
    description = serializers.CharField(source="shop_description", read_only=True)
    views = serializers.IntegerField(source="shop_views", read_only=True)
    messages = serializers.SerializerMethodField()
    products = serializers.IntegerField(source="products.count", read_only=True)
    owner = serializers.CharField(source="shop_display_name", read_only=True)
    creatorName = serializers.SerializerMethodField()
    ownerId = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.EmailField(read_only=True)
    phone = serializers.CharField(read_only=True)
    address = serializers.SerializerMethodField()
    website = serializers.SerializerMethodField()
    facebook = serializers.SerializerMethodField()
    instagram = serializers.SerializerMethodField()
    tiktok = serializers.SerializerMethodField()
    whatsapp = serializers.SerializerMethodField()
    shopImage = serializers.SerializerMethodField()
    creatorPhoto = serializers.SerializerMethodField()
    productList = serializers.SerializerMethodField()
    reviewList = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "category",
            "status",
            "rating",
            "reviewCount",
            "createdAt",
            "description",
            "views",
            "messages",
            "products",
            "owner",
            "creatorName",
            "ownerId",
            "email",
            "phone",
            "address",
            "website",
            "facebook",
            "instagram",
            "tiktok",
            "whatsapp",
            "shopImage",
            "creatorPhoto",
            "productList",
            "reviewList",
        ]

    def get_name(self, obj):
        return obj.shop_display_name

    def get_creatorName(self, obj):
        name = " ".join(
            part.strip()
            for part in (obj.first_name, getattr(obj, "last_name", ""))
            if part and str(part).strip()
        )
        return name or obj.username

    def get_category(self, obj):
        return obj.shop_category.name if obj.shop_category else ""

    def _validated_boutique(self, obj):
        return obj.boutiques.filter(status=Boutique.Status.VALIDATED).order_by("-created_at").first()

    def get_address(self, obj):
        return obj.adresse

    def get_shopImage(self, obj):
        if not obj.shop_image:
            return None
        request = self.context.get("request")
        url = obj.shop_image.url
        return request.build_absolute_uri(url) if request else url

    def get_creatorPhoto(self, obj):
        if not obj.profile_pic:
            return None
        request = self.context.get("request")
        url = obj.profile_pic.url
        return request.build_absolute_uri(url) if request else url

    def get_website(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.website if boutique else ""

    def get_facebook(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.facebook if boutique else ""

    def get_instagram(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.instagram if boutique else ""

    def get_tiktok(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.tiktok if boutique else ""

    def get_whatsapp(self, obj):
        boutique = self._validated_boutique(obj)
        return boutique.whatsapp if boutique else ""

    def get_rating(self, obj):
        return round(obj.shop_rating() or 0, 1)

    def get_reviewCount(self, obj):
        return obj.shop_review_count()

    def get_messages(self, obj):
        return obj.sent_messages.count() + obj.received_messages.count()

    def get_productList(self, obj):
        products = obj.products.filter(status=Product.Status.ACTIVE).order_by("name")
        return ProductSerializer(products, many=True).data

    def get_reviewList(self, obj):
        from favoris.models import Favorite

        reviews = Favorite.objects.filter(product__owner=obj)[:5]
        return ReviewSerializer(reviews, many=True).data


class BoutiqueSerializer(serializers.ModelSerializer):
    """Reçoit directement les clés envoyées par le formulaire /louer-espace."""

    companyName = serializers.CharField(source="company_name", max_length=150)
    ownerName = serializers.CharField(source="owner_name", max_length=150)
    otherNeighborhood = serializers.CharField(
        source="other_neighborhood",
        max_length=100,
        required=False,
        allow_blank=True,
    )
    ownerId = serializers.IntegerField(source="owner_id", read_only=True)
    ownerUsername = serializers.CharField(source="owner.username", read_only=True)
    date = serializers.DateTimeField(source="created_at", read_only=True)
    owner = serializers.SerializerMethodField()

    class Meta:
        model = Boutique
        fields = [
            "id",
            "companyName",
            "ownerName",
            "industry",
            "email",
            "phone",
            "whatsapp",
            "slogan",
            "facebook",
            "instagram",
            "tiktok",
            "website",
            "province",
            "commune",
            "neighborhood",
            "otherNeighborhood",
            "ownerId",
            "ownerUsername",
            "status",
            "date",
            "created_at",
            "owner",
        ]
        read_only_fields = ["status", "created_at"]

    def get_owner(self, obj):
        if obj.owner is None:
            return None
        return {
            "id": obj.owner.id,
            "username": obj.owner.username,
            "email": obj.owner.email,
            "first_name": obj.owner.first_name,
            "role": obj.owner.role,
        }

    def validate(self, attrs):
        if attrs.get("neighborhood") == "Autre" and not attrs.get("other_neighborhood"):
            raise serializers.ValidationError(
                {"otherNeighborhood": "Précisez le quartier."}
            )
        return attrs
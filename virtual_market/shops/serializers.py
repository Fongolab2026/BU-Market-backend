from rest_framework import serializers

from users.models import User
from products.serializers import ProductSerializer
from favoris.serializers import ReviewSerializer
from .models import BoutiqueRequest, ShopReview


class BoutiqueOwnerSerializer(serializers.ModelSerializer):
    """Représentation minimale du propriétaire attendue par l'admin."""

    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "name"]

    def get_name(self, obj):
        full = f"{obj.first_name} {obj.last_name}".strip()
        return full or obj.username


class BoutiqueRequestSerializer(serializers.ModelSerializer):
    """Serializer « camelCase » consommé par la page /louer-espace et l'admin."""

    companyName = serializers.CharField(source="company_name")
    ownerName = serializers.CharField(
        source="owner_name", required=False, allow_blank=True
    )
    industry = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    whatsapp = serializers.CharField(required=False, allow_blank=True)
    slogan = serializers.CharField(required=False, allow_blank=True)
    facebook = serializers.CharField(required=False, allow_blank=True)
    instagram = serializers.CharField(required=False, allow_blank=True)
    tiktok = serializers.CharField(required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True)
    province = serializers.CharField(required=False, allow_blank=True)
    commune = serializers.CharField(required=False, allow_blank=True)
    neighborhood = serializers.CharField(required=False, allow_blank=True)
    otherNeighborhood = serializers.CharField(
        source="other_neighborhood", required=False, allow_blank=True
    )
    date = serializers.DateTimeField(source="created_at", read_only=True)
    owner = BoutiqueOwnerSerializer(read_only=True)

    class Meta:
        model = BoutiqueRequest
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
            "status",
            "date",
            "owner",
        ]
        read_only_fields = ["status"]


class ShopSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    status = serializers.CharField(source="shop_status", read_only=True)
    rating = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="date_joined", read_only=True)
    description = serializers.CharField(source="shop_description", read_only=True)
    shopImage = serializers.SerializerMethodField()
    views = serializers.IntegerField(source="shop_views", read_only=True)
    messages = serializers.SerializerMethodField()
    products = serializers.IntegerField(source="products.count", read_only=True)
    owner = serializers.CharField(source="shop_display_name", read_only=True)
    ownerId = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.EmailField(read_only=True)
    phone = serializers.CharField(read_only=True)
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
            "shopImage",
            "views",
            "messages",
            "products",
            "owner",
            "ownerId",
            "email",
            "phone",
            "productList",
            "reviewList",
        ]

    def get_name(self, obj):
        return obj.shop_display_name

    def get_category(self, obj):
        return obj.shop_category.name if obj.shop_category else ""

    def get_shopImage(self, obj):
        if not obj.shop_image:
            return None
        request = self.context.get("request")
        url = obj.shop_image.url
        return request.build_absolute_uri(url) if request else url

    def get_rating(self, obj):
        return round(obj.shop_rating() or 0, 1)

    def get_reviewCount(self, obj):
        return obj.shop_review_count()

    def get_messages(self, obj):
        return obj.sent_messages.count() + obj.received_messages.count()

    def get_productList(self, obj):
        products = obj.products.filter(status="active").prefetch_related("images")[:5]
        return ProductSerializer(
            products, many=True, context=self.context
        ).data

    def get_reviewList(self, obj):
        from favoris.models import Favorite

        # Uniquement les vrais avis (les favoris sans commentaire sont exclus).
        reviews = Favorite.objects.reviews().filter(product__owner=obj)[:5]
        return ReviewSerializer(reviews, many=True).data


class ShopReviewSerializer(serializers.ModelSerializer):
    """Avis déposé sur une boutique entière (voir `ShopReview`)."""

    author = serializers.CharField(source="user.username", read_only=True)
    authorAvatar = serializers.SerializerMethodField()
    authorId = serializers.IntegerField(source="user.id", read_only=True)
    note = serializers.IntegerField(source="stars", min_value=1, max_value=5)
    comment = serializers.CharField(
        trim_whitespace=True, min_length=3, max_length=2000
    )
    date = serializers.DateTimeField(source="created_at", read_only=True)
    shopId = serializers.IntegerField(source="shop.id", read_only=True)
    shopName = serializers.SerializerMethodField()

    class Meta:
        model = ShopReview
        fields = [
            "id",
            "shop",
            "author",
            "authorAvatar",
            "authorId",
            "note",
            "comment",
            "date",
            "status",
            "shopId",
            "shopName",
        ]
        read_only_fields = ["status"]

    def validate_shop(self, shop):
        if shop.role != User.Role.SELLER:
            raise serializers.ValidationError(
                "Seules les boutiques de vendeurs peuvent être notées."
            )
        if shop.shop_status != User.ShopStatus.VALIDATED:
            raise serializers.ValidationError(
                "Cette boutique n'est pas encore validée."
            )
        return shop

    def validate(self, attrs):
        if (
            self.instance is not None
            and "shop" in attrs
            and attrs["shop"].pk != self.instance.shop_id
        ):
            raise serializers.ValidationError(
                "Impossible de changer la boutique associée à un avis."
            )
        return attrs

    def get_authorAvatar(self, obj):
        if not obj.user or not obj.user.profile_pic:
            return None
        request = self.context.get("request")
        url = obj.user.profile_pic.url
        return request.build_absolute_uri(url) if request is not None else url

    def get_shopName(self, obj):
        return obj.shop.shop_display_name

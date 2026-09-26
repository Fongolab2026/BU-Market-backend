from rest_framework import serializers

from users.models import User
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

    def get_rating(self, obj):
        return round(obj.shop_rating() or 0, 1)

    def get_reviewCount(self, obj):
        return obj.shop_review_count()

    def get_messages(self, obj):
        return obj.sent_messages.count() + obj.received_messages.count()

    def get_productList(self, obj):
        return ProductSerializer(obj.products.all()[:5], many=True).data

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
        ]
        read_only_fields = ["status", "created_at"]

    def validate(self, attrs):
        if attrs.get("neighborhood") == "Autre" and not attrs.get("other_neighborhood"):
            raise serializers.ValidationError(
                {"otherNeighborhood": "Précisez le quartier."}
            )
        return attrs

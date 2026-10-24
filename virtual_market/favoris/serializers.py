from rest_framework import serializers
from .models import Favorite, Review


class FavoriteSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    price = serializers.DecimalField(
        source="product.price", max_digits=10, decimal_places=2, read_only=True
    )
    details = serializers.CharField(source="product.details", read_only=True)
    category = serializers.IntegerField(source="product.category_id", read_only=True)
    product_status = serializers.CharField(source="product.status", read_only=True)
    main_image = serializers.SerializerMethodField()
    shopName = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = [
            "id",
            "user",
            "user_username",
            "product",
            "product_name",
            "price",
            "details",
            "category",
            "product_status",
            "main_image",
            "shopName",
            "stars",
            "comment",
            "status",
            "created_at",
        ]
        read_only_fields = ["user"]

    def get_main_image(self, obj):
        images = list(obj.product.images.all())
        main = next((img for img in images if img.is_main), None)
        if main is None and images:
            main = images[0]
        if main is None or not main.image:
            return None
        request = self.context.get("request")
        url = main.image.url
        return request.build_absolute_uri(url) if request is not None else url

    def get_shopName(self, obj):
        return obj.product.owner.shop_display_name

    def validate_stars(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Les étoiles doivent être comprises entre 1 et 5.")
        return value


class ReviewSerializer(serializers.ModelSerializer):
    authorId = serializers.IntegerField(source="user_id", read_only=True)
    author = serializers.CharField(source="user.username", read_only=True)
    authorAvatar = serializers.SerializerMethodField()
    note = serializers.IntegerField(source="stars", min_value=1, max_value=5)
    comment = serializers.CharField(allow_blank=True, required=False)
    date = serializers.DateTimeField(source="created_at", read_only=True)
    shopId = serializers.IntegerField(source="product.owner_id", read_only=True)
    shopName = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "product",
            "authorId",
            "author",
            "authorAvatar",
            "note",
            "comment",
            "date",
            "status",
            "shopId",
            "shopName",
        ]
        read_only_fields = ["status"]

    def get_authorAvatar(self, obj):
        if not obj.user or not obj.user.profile_pic:
            return None
        request = self.context.get("request")
        url = obj.user.profile_pic.url
        return request.build_absolute_uri(url) if request is not None else url

    def get_shopName(self, obj):
        return obj.product.owner.shop_display_name

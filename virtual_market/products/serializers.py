from rest_framework import serializers
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

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["owner"]

    def get_main_image(self, obj):
        request = self.context.get("request")
        main = obj.images.filter(is_main=True).first() or obj.images.first()
        url = main.image.url if main else None
        if url and request is not None:
            return request.build_absolute_uri(url)
        return url
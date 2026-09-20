from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "created_at", "count"]
        read_only_fields = ["slug", "created_at", "count"]
from rest_framework import serializers
from categorie.models import Category
from .models import PlatformSettings


class ModerationItemSerializer(serializers.Serializer):
    """Élément de la file de modération : { id, type, title, owner, date, status }"""

    id = serializers.IntegerField(read_only=True)
    type = serializers.SerializerMethodField()
    title = serializers.CharField(source="username", read_only=True)
    owner = serializers.CharField(source="username", read_only=True)
    date = serializers.DateTimeField(source="date_joined", read_only=True)
    status = serializers.SerializerMethodField()

    def get_type(self, obj):
        return "seller"

    def get_status(self, obj):
        return "pending"


class PlatformSettingsSerializer(serializers.ModelSerializer):
    platformName = serializers.CharField(source="platform_name")
    supportEmail = serializers.EmailField(source="support_email")
    defaultLanguage = serializers.CharField(source="default_language")
    categories = serializers.SerializerMethodField()

    class Meta:
        model = PlatformSettings
        fields = [
            "platformName",
            "supportEmail",
            "phone",
            "defaultLanguage",
            "currency",
            "moderation",
            "notifications",
            "categories",
        ]

    def get_categories(self, obj):
        return [
            {"id": category.id, "name": category.name, "count": category.products.count()}
            for category in Category.objects.all().order_by("name")
        ]
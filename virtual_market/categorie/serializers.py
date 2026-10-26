from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(source="products.count", read_only=True)
    # Visuel : lisible (URL renvoyée à la lecture) et inscriptable (upload
    # multipart envoyé par le formulaire vendeur/admin).
    image = serializers.ImageField(required=False, allow_null=True)
    # Champ d'écriture seule : permet de retirer un visuel sans en renvoyer un.
    remove_image = serializers.BooleanField(
        required=False, write_only=True, default=False
    )
    # En multipart, un BooleanField absent vaut `False` chez DRF
    # (`default_empty_html`) : on force `None` pour distinguer « non fourni »
    # de « désactivé », sinon créer une catégorie avec une image la créait
    # inactivée. `create`/`update` traitent ensuite la valeur nulle.
    active = serializers.BooleanField(required=False, allow_null=True, default=None)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "image",
            "remove_image",
            "active",
            "created_at",
            "count",
        ]
        read_only_fields = ["slug", "created_at", "count"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        image = data.get("image")
        request = self.context.get("request")
        if image and request:
            # URL absolue : le front réécrit ensuite vers l'origine API.
            data["image"] = request.build_absolute_uri(image)
        return data

    def create(self, validated_data):
        # `remove_image` n'existe pas sur le modèle : DRF tenterait
        # sinon `Category.objects.create(remove_image=...)`.
        validated_data.pop("remove_image", False)
        if validated_data.get("active") is None:
            validated_data["active"] = True  # défaut métier : catégorie visible
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.pop("remove_image", False) and instance.image:
            instance.image.delete(save=False)
            instance.image = None
        if validated_data.get("active") is None:
            # Non fourni (multipart) ou null : on laisse le statut actuel
            # plutôt que de réinitialiser la catégorie à l'inactive.
            validated_data.pop("active", None)
        return super().update(instance, validated_data)

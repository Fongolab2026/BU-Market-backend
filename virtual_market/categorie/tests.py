import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category
from users.models import User

# PNG 1x1 minimal, suffisant pour valider l'upload d'un `ImageField`.
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="bumarket-test-media-"))
class CategoryImageTests(APITestCase):
    """Visuel des catégories : upload multipart par un vendeur ou un admin."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username="vendeur",
            password="pass12345",
            phone="0303030310",
            role=User.Role.SELLER,
        )
        self.buyer = User.objects.create_user(
            username="client", password="pass12345", phone="0404040410"
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="pass12345",
            phone="0505050510",
            role=User.Role.ADMIN,
        )
        self.list_url = reverse("category-list")

    @staticmethod
    def upload(name="Épicerie"):
        return SimpleUploadedFile("categorie.png", TINY_PNG, content_type="image/png")

    def test_list_is_public(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buyer_cannot_create_category(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(self.list_url, {"name": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_can_create_category_with_image(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(
            self.list_url,
            {
                "name": "Épicerie fine",
                "description": "Produits frais",
                "icon": "apple",
                "image": self.upload(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("/media/categories/", response.data["image"])

    def test_seller_can_create_category_without_image(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(
            self.list_url,
            {"name": "Sans visuel", "icon": "package"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["image"])

    def test_admin_can_replace_and_remove_image(self):
        category = Category.objects.create(name="Artisanat", icon="wrench")
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            reverse("category-detail", args=[category.id]),
            {"image": self.upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/media/categories/", response.data["image"])

        response = self.client.patch(
            reverse("category-detail", args=[category.id]),
            {"remove_image": True},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["image"])
        category.refresh_from_db()
        self.assertFalse(bool(category.image))

    def test_multipart_create_without_active_stays_active(self):
        """Piège DRF : en multipart, un BooleanField absent vaut `False`.

        Créer une catégorie avec une image ne doit pas la créer inactivée.
        """
        self.client.force_authenticate(self.seller)
        response = self.client.post(
            self.list_url,
            {"name": "Fruits", "icon": "apple", "image": self.upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["active"])

    def test_multipart_update_without_active_keeps_status(self):
        category = Category.objects.create(name="Masquée", active=False)
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            reverse("category-detail", args=[category.id]),
            {"name": "Masquée bis", "image": self.upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["active"])
        category.refresh_from_db()
        self.assertFalse(category.active)

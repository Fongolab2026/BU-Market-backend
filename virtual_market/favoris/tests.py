from categorie.models import Category
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Product
from users.models import User


class FavorisAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="joe", password="pass12345", phone="0101010101"
        )
        self.other = User.objects.create_user(
            username="bob", password="pass12345", phone="0202020202"
        )
        self.category = Category.objects.create(name="Vêtements")
        self.product = Product.objects.create(
            name="Vest",
            price="12.00",
            details="Description",
            category=self.category,
            owner=self.user,
        )
        self.list_url = reverse("favorite-list")

    def test_requires_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_favorite_sets_user_and_default_stars(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.list_url,
            {"product": self.product.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["stars"], 1)

    def test_create_favorite_with_stars(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.list_url,
            {"product": self.product.id, "stars": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["stars"], 5)

    def test_rejects_stars_out_of_range(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.list_url,
            {"product": self.product.id, "stars": 7},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_favorite_is_rejected(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            self.list_url,
            {"product": self.product.id},
            format="json",
        )
        response = self.client.post(
            self.list_url,
            {"product": self.product.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_sees_only_own_favorites(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            self.list_url,
            {"product": self.product.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 0)
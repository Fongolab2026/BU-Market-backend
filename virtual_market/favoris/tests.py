from categorie.models import Category
from django.urls import reverse
from notification.models import Notification
from rest_framework import status
from rest_framework.test import APITestCase

from favoris.models import Favorite, Review
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
            # `products.signals` supprime les produits sans stock au save.
            stock=10,
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
        # Les favoris ont maintenant stars=1 par défaut (les avis passent par l'endpoint reviews)
        self.assertEqual(response.data["stars"], 1)

    def test_create_favorite_ignores_stars(self):
        """Un favori ignore le champ stars (toujours 1), les avis passent par /reviews/."""
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.list_url,
            {"product": self.product.id, "stars": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["stars"], 1)

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
        # La réponse est paginée : vérifier results ou count
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 0)


class ReviewAPITests(APITestCase):
    """Avis produits : client ET vendeur peuvent noter, jamais leur propre produit."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username="vendeur",
            password="pass12345",
            phone="0303030303",
            role=User.Role.SELLER,
            shop_name="Boutique Test",
            shop_status=User.ShopStatus.VALIDATED,
        )
        self.buyer = User.objects.create_user(
            username="acheteur", password="pass12345", phone="0404040404"
        )
        self.other = User.objects.create_user(
            username="confrere", password="pass12345", phone="0505050505"
        )
        self.admin = User.objects.create_user(
            username="moderateur",
            password="pass12345",
            phone="0606060606",
            role=User.Role.ADMIN,
        )
        self.category = Category.objects.create(name="Chaussures")
        self.product = Product.objects.create(
            name="Baskets",
            price="50.00",
            details="Confortables",
            category=self.category,
            owner=self.seller,
            stock=10,
        )
        self.list_url = reverse("review-list")
        self.payload = {
            "product": self.product.id,
            "note": 5,
            "comment": "Super produit, livraison rapide.",
        }

    @staticmethod
    def results(response):
        return response.data.get("results", response.data)

    def test_create_requires_authentication(self):
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_buyer_can_publish_review_with_note_and_comment(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["note"], 5)
        self.assertEqual(response.data["comment"], self.payload["comment"])
        self.assertEqual(response.data["author"], "acheteur")
        self.assertEqual(response.data["shopName"], "Boutique Test")

    def test_seller_can_review_another_seller_product(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_seller_cannot_review_own_product(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_review_is_rejected(self):
        self.client.force_authenticate(self.buyer)
        self.client.post(self.list_url, self.payload, format="json")
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comment_is_required_and_long_enough(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            self.list_url,
            {**self.payload, "comment": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_favorite_stays_a_favorite_when_reviewing(self):
        """Favori et avis sont deux lignes distinctes."""
        self.client.force_authenticate(self.buyer)
        favorite_url = reverse("favorite-list")
        self.client.post(favorite_url, {"product": self.product.id}, format="json")

        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Favorite.objects.filter(user=self.buyer, product=self.product).count(),
            1,
        )
        self.assertEqual(
            Favorite.objects.exclude(comment="").count(),
            0,
            "Un favori ne porte plus d'avis : la note vit dans Review.",
        )
        self.assertEqual(
            Review.objects.filter(user=self.buyer, product=self.product).count(),
            1,
        )

    def test_public_list_returns_only_visible_reviews_of_the_product(self):
        self.client.force_authenticate(self.buyer)
        self.client.post(self.list_url, self.payload, format="json")
        self.client.force_authenticate(self.other)
        hidden = Review.objects.get(user=self.buyer, product=self.product)
        hidden.status = Review.Status.HIDDEN
        hidden.save()

        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.list_url}?product={self.product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.results(response)
        self.assertEqual(len(results), 0)

    def test_list_without_filter_returns_own_reviews_only(self):
        self.client.force_authenticate(self.buyer)
        self.client.post(self.list_url, self.payload, format="json")

        self.client.force_authenticate(self.other)
        response = self.client.get(self.list_url)
        self.assertEqual(len(self.results(response)), 0)

        self.client.force_authenticate(self.buyer)
        response = self.client.get(self.list_url)
        self.assertEqual(len(self.results(response)), 1)

    def test_admin_sees_every_review(self):
        self.client.force_authenticate(self.buyer)
        self.client.post(self.list_url, self.payload, format="json")
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url)
        self.assertEqual(len(self.results(response)), 1)

    def test_report_notifies_admins(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")

        self.client.force_authenticate(self.other)
        response = self.client.post(
            f"{self.list_url}{created.data['id']}/report/", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["reported"])
        self.assertEqual(
            Notification.objects.filter(
                user=self.admin, title__icontains="signalé"
            ).count(),
            1,
        )

    def test_cannot_report_own_review(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")
        response = self.client.post(
            f"{self.list_url}{created.data['id']}/report/", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_can_edit_and_delete_their_review(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")

        response = self.client.patch(
            f"{self.list_url}{created.data['id']}/",
            {"note": 3, "comment": "Correct mais perfectible."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["note"], 3)

        response = self.client.delete(f"{self.list_url}{created.data['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_buyer_cannot_hide_review(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")
        response = self.client.patch(
            f"{self.list_url}{created.data['id']}/hide/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
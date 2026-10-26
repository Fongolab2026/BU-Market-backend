from django.urls import reverse
from notification.models import Notification
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ShopReview
from users.models import User


class ShopReviewAPITests(APITestCase):
    """Avis boutique : clients et vendeurs notent une boutique tierce."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username="atelier",
            password="pass12345",
            phone="0707070707",
            role=User.Role.SELLER,
            shop_name="Atelier du centre",
            shop_status=User.ShopStatus.VALIDATED,
        )
        self.pending_shop = User.objects.create_user(
            username="en_attente",
            password="pass12345",
            phone="0808080808",
            role=User.Role.SELLER,
            shop_name="Boutique en attente",
            shop_status=User.ShopStatus.PENDING,
        )
        self.buyer = User.objects.create_user(
            username="cliente", password="pass12345", phone="0909090909"
        )
        self.confrere = User.objects.create_user(
            username="confrere",
            password="pass12345",
            phone="0101010100",
            role=User.Role.SELLER,
            shop_name="Autre boutique",
            shop_status=User.ShopStatus.VALIDATED,
        )
        self.admin = User.objects.create_user(
            username="moderateur",
            password="pass12345",
            phone="0202020200",
            role=User.Role.ADMIN,
        )
        self.list_url = reverse("shop-review-list")
        self.payload = {
            "shop": self.seller.id,
            "note": 4,
            "comment": "Très belle boutique, je recommande.",
        }

    @staticmethod
    def results(response):
        return response.data.get("results", response.data)

    def test_create_requires_authentication(self):
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_buyer_can_review_validated_shop(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["note"], 4)
        self.assertEqual(response.data["shopName"], "Atelier du centre")
        self.assertEqual(response.data["author"], "cliente")

    def test_seller_can_review_another_shop(self):
        self.client.force_authenticate(self.confrere)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_seller_cannot_review_own_shop(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_shop_cannot_be_reviewed(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            self.list_url,
            {**self.payload, "shop": self.pending_shop.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_review_is_rejected(self):
        self.client.force_authenticate(self.buyer)
        self.client.post(self.list_url, self.payload, format="json")
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_list_by_shop_shows_visible_reviews(self):
        self.client.force_authenticate(self.buyer)
        self.client.post(self.list_url, self.payload, format="json")

        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.list_url}?shop={self.seller.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(self.results(response)), 1)

        # Un avis masqué n'apparaît plus publiquement.
        review = ShopReview.objects.get(shop=self.seller)
        review.status = ShopReview.Status.HIDDEN
        review.save()
        response = self.client.get(f"{self.list_url}?shop={self.seller.id}")
        self.assertEqual(len(self.results(response)), 0)

    def test_list_without_filter_returns_own_reviews(self):
        self.client.force_authenticate(self.buyer)
        self.client.post(self.list_url, self.payload, format="json")

        self.client.force_authenticate(self.confrere)
        response = self.client.get(self.list_url)
        self.assertEqual(len(self.results(response)), 0)

        self.client.force_authenticate(self.buyer)
        response = self.client.get(self.list_url)
        self.assertEqual(len(self.results(response)), 1)

    def test_report_notifies_admins(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")

        self.client.force_authenticate(self.confrere)
        response = self.client.post(
            f"{self.list_url}{created.data['id']}/report/", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["reported"])
        self.assertTrue(
            Notification.objects.filter(user=self.admin).exists()
        )

    def test_owner_can_update_and_delete(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")

        response = self.client.patch(
            f"{self.list_url}{created.data['id']}/",
            {"note": 5, "comment": "Excellent accueil !"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["note"], 5)

        response = self.client.delete(f"{self.list_url}{created.data['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_buyer_cannot_hide_review(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")
        response = self.client.patch(
            f"{self.list_url}{created.data['id']}/hide/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_moderates_visibility(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(self.list_url, self.payload, format="json")

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"{self.list_url}{created.data['id']}/hide/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ShopReview.Status.HIDDEN)

    def test_shop_rating_aggregates_product_and_shop_reviews(self):
        """La note de la boutique cumule avis produits et avis de boutique."""
        from categorie.models import Category
        from favoris.models import Favorite
        from products.models import Product

        category = Category.objects.create(name="Outillage")
        product = Product.objects.create(
            name="Marteau",
            price="10.00",
            details="Solide",
            category=category,
            owner=self.seller,
            stock=10,
        )
        Favorite.objects.create(
            user=self.confrere, product=product, stars=3, comment="Correct."
        )
        ShopReview.objects.create(
            user=self.buyer, shop=self.seller, stars=5, comment="Excellent accueil."
        )

        self.assertEqual(self.seller.shop_review_count(), 2)
        self.assertEqual(round(self.seller.shop_rating(), 2), 4.0)

        # Un avis masqué ne compte plus dans la note.
        shop_review = ShopReview.objects.get(shop=self.seller, user=self.buyer)
        shop_review.status = ShopReview.Status.HIDDEN
        shop_review.save()
        self.assertEqual(self.seller.shop_review_count(), 1)
        self.assertEqual(round(self.seller.shop_rating(), 2), 3.0)

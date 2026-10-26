from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import reviews, views

router = DefaultRouter()
router.register("shops", views.ShopViewSet, basename="shop")
router.register("boutiques", views.BoutiqueRequestViewSet, basename="boutique")
router.register("shop-reviews", reviews.ShopReviewViewSet, basename="shop-review")

urlpatterns = [
    path("", include(router.urls)),
]
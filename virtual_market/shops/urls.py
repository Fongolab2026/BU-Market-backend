from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("shops", views.ShopViewSet, basename="shop")
router.register("boutiques", views.BoutiqueViewSet, basename="boutique")

urlpatterns = [
    path("", include(router.urls)),
]
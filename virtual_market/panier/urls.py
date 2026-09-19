from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

cart_router = DefaultRouter()
cart_router.register("", views.CartViewSet, basename="cart")

item_router = DefaultRouter()
item_router.register("items", views.CartItemViewSet, basename="cartitem")

urlpatterns = [
    path("", include(cart_router.urls)),
    path("", include(item_router.urls)),
]
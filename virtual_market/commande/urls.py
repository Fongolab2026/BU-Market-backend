from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

order_router = DefaultRouter()
order_router.register("", views.OrderViewSet, basename="order")

item_router = DefaultRouter()
item_router.register("items", views.OrderItemViewSet, basename="orderitem")

urlpatterns = [
    path("", include(order_router.urls)),
    path("", include(item_router.urls)),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("favorites", views.FavoriteViewSet, basename="favorite")

urlpatterns = [
    path("", include(router.urls)),
]
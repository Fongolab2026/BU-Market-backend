from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("favorites", views.FavoriteViewSet, basename="favorite")

review_router = DefaultRouter()
review_router.register("reviews", views.ReviewViewSet, basename="review")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(review_router.urls)),
]
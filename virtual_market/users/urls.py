from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import UserViewset

router = routers.DefaultRouter()
router.register('users', UserViewset, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', TokenObtainPairView.as_view(), name="token_access"),
    path('refresh/', TokenRefreshView.as_view(), name="token_refresh")
]

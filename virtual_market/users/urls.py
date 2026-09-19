from django.urls import path, include
from .views import UserViewset
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register('users', UserViewset, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', TokenObtainPairView.as_view(), name="token_access"),
    path('auth/refresh/', TokenRefreshView.as_view(), name="token_refresh")
]

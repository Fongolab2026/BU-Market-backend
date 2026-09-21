"""
URL configuration for virtual_market project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import ApiRootView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/auth/login/', TokenObtainPairView.as_view(), name="token_access"),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name="token_refresh"),
    path('api/products/', include('products.urls')),
    path('api/users/', include('users.urls')),
    path('api/messages/', include('messages.urls')),
    path('api/categories/', include('categorie.urls')),
    path('api/carts/', include('panier.urls')),
    path('api/orders/', include('commande.urls')),
    path('api/notifications/', include('notification.urls')),
    path('api/favorites/', include('favoris.urls')),
    path('api/admin/', include('admin.urls')),
    path('api/shops/', include('shops.urls')),
    path('api/publications/', include('publications.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name="schema"),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

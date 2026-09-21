from django.urls import path, include

urlpatterns = [
    path('products/', include('products.urls')),
    path('users/', include('users.urls')),
    path('categories/', include('categorie.urls')),
    path('shops/', include('shops.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('favorites/', include('favorites.urls')),
    path('messages/', include('messages.urls')),
    path('notifications/', include('notifications.urls')),
]
from django.urls import path, include

urlpatterns = [
    path('auth/', include('users.urls')),
    path('products/', include('products.urls')),
    path('users/', include('users.urls')),
    path('categories/', include('categories.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('favorites/', include('favorites.urls')),
    path('messages/', include('messages.urls')),
    path('notifications/', include('notifications.urls')),
]
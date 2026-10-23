from django.urls import path, include

urlpatterns = [
    path('products/', include('products.urls')),
    path('users/', include('users.urls')),
    path('categories/', include('categorie.urls')),
    path('shops/', include('shops.urls')),
    path('carts/', include('panier.urls')),
    path('orders/', include('commande.urls')),
    path('favorites/', include('favoris.urls')),
    path('messages/', include('messages.urls')),
    path('notifications/', include('notification.urls')),
    path('admin/', include('admin.urls')),
    path('publications/', include('publications.urls')),
]

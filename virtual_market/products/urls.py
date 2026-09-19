from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'produit', views.ProductsView)
router.register(r'categories', views.CategoriesView)


urlpatterns =[
    path('', include(router.urls)),
]
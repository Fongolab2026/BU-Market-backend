from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductsView, basename='product')


urlpatterns =[
    path('', include(router.urls)),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'messages', views.MessagesView, basename='message')

urlpatterns = [
    path('', include(router.urls)),
]
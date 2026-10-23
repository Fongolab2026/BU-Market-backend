from django.urls import path, include
from rest_framework import routers
from .views import UserViewset

class UserRouter(routers.DefaultRouter):
    """Router qui contraint le lookup pk à être un entier."""
    def get_lookup_regex(self, viewset, lookup_prefix=""):
        return r"(?P<pk>\d+)"


router = UserRouter()
router.register('users', UserViewset, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]

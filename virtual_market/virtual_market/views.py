from rest_framework.response import Response
from rest_framework.views import APIView


class ApiRootView(APIView):
    permission_classes = []

    def get(self, request):
        base = request.build_absolute_uri("/")
        return Response(
            {
                "auth_login": base + "api/auth/login/",
                "auth_refresh": base + "api/auth/refresh/",
                "users": base + "api/users/",
                "products": base + "api/products/",
                "categories": base + "api/categories/",
                "carts": base + "api/carts/",
                "cart_items": base + "api/cart-items/",
                "orders": base + "api/orders/",
                "order_items": base + "api/order-items/",
                "messages": base + "api/messages/",
                "notifications": base + "api/notifications/",
                "schema": base + "api/schema/",
                "docs": base + "api/docs/",
                "admin": base + "admin/",
            }
        )
from datetime import timedelta

from django.utils import timezone
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from commande.models import Order
from messages.models import Message
from notification.models import Notification
from products.models import Product
from users.models import User
from users.permisions import IsAdminOrSuperAdmin

from .models import PlatformSettings
from .pagination import AdminPageNumberPagination
from .serializers import ModerationItemSerializer, PlatformSettingsSerializer


def _percent_change(current, previous):
    if previous == 0:
        return 100.0 if current else 0.0
    return round((current - previous) / previous * 100.0, 1)


def _kpi(cid, label, current, recent, previous, invert=False):
    change = _percent_change(recent, previous)
    up = recent >= previous
    trend = "down" if up else "up"
    if invert:
        trend = "up" if up else "down"
    tone = {"up": "positive", "down": "negative"}.get(trend, "neutral")
    return {
        "id": cid,
        "label": label,
        "value": current,
        "change": change,
        "trend": trend,
        "tone": tone,
    }


class AdminStatsView(APIView):
    """GET /api/admin/stats/ — KPI du tableau de bord admin."""

    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=6)
        prev_start = week_start - timedelta(days=7)

        def recent(field, qs):
            return qs.filter(**{f"{field}__date__gte": week_start}).count()

        def previous(field, qs):
            return qs.filter(
                **{
                    f"{field}__date__lt": week_start,
                    f"{field}__date__gte": prev_start,
                }
            ).count()

        users = User.objects.all()
        shops = User.objects.filter(role="seller", is_active=True)
        products = Product.objects.all()
        pending = User.objects.filter(role="seller", is_active=False)

        stats = [
            _kpi("users", "Utilisateurs", users.count(), recent("date_joined", users), previous("date_joined", users)),
            _kpi(
                "shops",
                "Boutiques actives",
                shops.count(),
                recent("date_joined", shops),
                previous("date_joined", shops),
            ),
            _kpi(
                "products",
                "Produits publiés",
                products.count(),
                recent("created_at", products),
                previous("created_at", products),
            ),
            _kpi(
                "moderation",
                "À modérer",
                pending.count(),
                recent("date_joined", pending),
                previous("date_joined", pending),
                invert=True,
            ),
        ]

        weekly_activity = [
            Order.objects.filter(created_at__date=today - timedelta(days=offset)).count()
            for offset in range(6, -1, -1)
        ]

        queue = ModerationItemSerializer(
            pending.order_by("-date_joined")[:5], many=True
        ).data

        return Response(
            {
                "stats": stats,
                "weeklyActivity": weekly_activity,
                "moderationQueue": queue,
            }
        )


class AdminActivityView(APIView):
    """GET /api/admin/activity/ — journal d'activité récent."""

    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        entries = []

        for user in User.objects.order_by("-date_joined")[:10]:
            entries.append(
                {
                    "id": f"user-{user.id}",
                    "title": user.username,
                    "description": "Nouveau compte enregistré",
                    "time": user.date_joined.isoformat(),
                    "kind": "user",
                }
            )

        for product in Product.objects.select_related("owner").order_by("-created_at")[:10]:
            entries.append(
                {
                    "id": f"product-{product.id}",
                    "title": product.name,
                    "description": f"Nouveau produit par {product.owner.username}",
                    "time": product.created_at.isoformat(),
                    "kind": "product",
                }
            )

        for order in Order.objects.select_related("user").order_by("-created_at")[:10]:
            entries.append(
                {
                    "id": f"order-{order.id}",
                    "title": f"Commande #{order.id}",
                    "description": f"{order.user.username} · {order.get_status_display()}",
                    "time": order.created_at.isoformat(),
                    "kind": "order",
                }
            )

        for message in Message.objects.select_related("sender", "receiver").order_by("-timestamp")[:10]:
            entries.append(
                {
                    "id": f"message-{message.id}",
                    "title": f"Message de {message.sender.username} à {message.receiver.username}",
                    "description": message.content[:100],
                    "time": message.timestamp.isoformat(),
                    "kind": "message",
                }
            )

        entries.sort(key=lambda entry: entry["time"], reverse=True)
        return Response(entries[:50])


class AdminModerationQueueView(ListAPIView):
    """GET /api/admin/moderation-queue/ — comptes boutiques en attente de validation."""

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = ModerationItemSerializer
    pagination_class = AdminPageNumberPagination
    queryset = User.objects.filter(role="seller", is_active=False).order_by("-date_joined")


class AdminMetaView(APIView):
    """GET /api/admin/meta/ — mappages attendus par l'interface admin."""

    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        return Response(
            {
                "roles": {
                    "superadmin": "admin",
                    "admin": "admin",
                    "seller": "merchant",
                    "buyer": "client",
                },
                "orderStatuses": [
                    {"value": value, "label": label}
                    for value, label in Order.Status.choices
                ],
                "notificationTypes": [
                    {"value": value, "label": label}
                    for value, label in Notification.Type.choices
                ],
                "userStatuses": ["active", "pending", "suspended"],
                "pagination": {
                    "perPage": AdminPageNumberPagination.page_size,
                    "format": ["results", "total", "totalPages", "page", "perPage"],
                },
            }
        )


class PlatformSettingsView(RetrieveUpdateAPIView):
    """GET/PATCH /api/admin/settings/ — paramètres de la plateforme."""

    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = PlatformSettingsSerializer
    queryset = PlatformSettings.objects.all()

    def get_object(self):
        return PlatformSettings.load()
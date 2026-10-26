from django.db.models import Q

from .models import Notification


def notify_admins(title: str, message: str, type: str = "alert") -> int:
    """Notifie tous les administrateurs (modération, alertes système).

    Retourne le nombre d'administrateurs prévenus.
    """
    from users.models import User

    admins = User.objects.filter(
        Q(is_superuser=True) | Q(role__in=("admin", "superadmin"))
    ).distinct()
    Notification.objects.bulk_create(
        [
            Notification(user=admin, title=title, message=message, type=type)
            for admin in admins
        ]
    )
    return len(admins)

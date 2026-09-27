"""Creer un super-admin par defaut.

Usage:
    python manage.py create_admin           # cree admin/admin1234 si absent
    python manage.py create_admin --force   # recrée le mot de passe
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Cree un super-admin par defaut (username=admin, password=admin1234)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force la reinitialisation du mot de passe si l'admin existe deja.",
        )

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@bumarket.app",
                "first_name": "Admin",
                "role": User.Role.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "status": User.AccountStatus.ACTIVE,
            },
        )

        if created or options["force"]:
            admin.set_password("admin1234")
            admin.role = User.Role.SUPER_ADMIN
            admin.is_staff = True
            admin.is_superuser = True
            admin.is_active = True
            admin.status = User.AccountStatus.ACTIVE
            admin.save()
            self.stdout.write(self.style.SUCCESS(
                f"Super-admin cree : username=admin, password=admin1234"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Super-admin existe deja. Utilisez --force pour reinitialiser le mot de passe."
            ))
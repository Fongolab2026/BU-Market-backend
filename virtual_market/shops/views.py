from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from admin.pagination import AdminPageNumberPagination
from categorie.models import Category
from products.models import Product
from products.models import ProductImage
from products.serializers import ProductSerializer
from users.models import User
from users.permisions import IsAdminOrSuperAdmin
from .models import BoutiqueRequest
from .serializers import BoutiqueRequestSerializer, ShopSerializer


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ShopSerializer
    queryset = (
        User.objects.filter(role=User.Role.SELLER)
        .select_related("shop_category")
        .order_by("-date_joined")
    )

    def get_permissions(self):
        # Le catalogue de boutiques validées est public. Les outils vendeur
        # restent réservés aux utilisateurs connectés.
        if self.action in ("list", "retrieve"):
            permission_classes = [AllowAny]
        elif self.action in ("my_shop", "add_product", "update_info"):
            permission_classes = [IsAuthenticated]
        else:
            # validate / suspend / set_status : administration uniquement.
            permission_classes = [IsAdminOrSuperAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        qs = super().get_queryset()
        # Les visiteurs et clients ne voient que les boutiques validées.
        user = self.request.user
        is_admin = user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "superadmin")
        )
        if not is_admin:
            qs = qs.filter(shop_status=User.ShopStatus.VALIDATED)
        search = self.request.query_params.get("search")
        shop_status = self.request.query_params.get("status")
        if search:
            qs = qs.filter(
                Q(username__icontains=search) | Q(shop_name__icontains=search)
            )
        if shop_status:
            qs = qs.filter(shop_status=shop_status)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.shop_views += 1
        instance.save(update_fields=["shop_views"])
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="validate")
    def validate(self, request, pk=None):
        shop = self.get_object()
        shop.shop_status = User.ShopStatus.VALIDATED
        shop.save()
        return Response(self.get_serializer(shop).data)

    @action(detail=True, methods=["patch"], url_path="suspend")
    def suspend(self, request, pk=None):
        shop = self.get_object()
        shop.shop_status = User.ShopStatus.SUSPENDED
        shop.save()
        return Response(self.get_serializer(shop).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        shop = self.get_object()
        shop.shop_status = request.data.get("status", shop.shop_status)
        shop.save()
        return Response(self.get_serializer(shop).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="products",
        parser_classes=[MultiPartParser, FormParser],
    )
    def add_product(self, request, pk=None):
        shop = User.objects.filter(pk=pk).first()
        if shop is None:
            return Response(
                {"detail": "Boutique introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        is_admin = _is_admin(request.user)
        if not (is_admin or shop.pk == request.user.pk):
            return Response(
                {"detail": "Action non autorisée."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not is_admin and (
            not shop.is_seller or shop.shop_status != User.ShopStatus.VALIDATED
        ):
            return Response(
                {"detail": "La boutique doit être validée avant de publier des produits."},
                status=status.HTTP_403_FORBIDDEN,
            )
        images = request.FILES.getlist("images")
        if not images:
            return Response(
                {"images": ["Au moins une photo du produit est obligatoire."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("stock", 0) <= 0:
            return Response(
                {"stock": ["Le stock doit être supérieur à zéro."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from admin.models import PlatformSettings

        require_approval = PlatformSettings.load().moderation.get(
            "requireProductApproval", False
        )
        product_status = Product.Status.INACTIVE if require_approval else Product.Status.ACTIVE
        product = serializer.save(owner=shop, status=product_status)
        for index, image in enumerate(images):
            ProductImage.objects.create(
                product=product, image=image, is_main=(index == 0)
            )
        if require_approval:
            from publications.models import PublicationRequest

            PublicationRequest.objects.create(product=product, seller=shop)
        serializer = ProductSerializer(product, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="my-shop")
    def my_shop(self, request):
        """Boutique du vendeur connecté (utilisée par l'espace marchand)."""
        user = request.user
        if not (user.is_seller or user.shop_name):
            return Response(
                {"detail": "Aucune boutique pour cet utilisateur."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self.get_serializer(user).data)

    @action(
        detail=True,
        methods=["patch"],
        url_path="info",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def update_info(self, request, pk=None):
        """Met à jour l'identité de la boutique (nom, description, catégorie, image)."""
        shop = User.objects.filter(pk=pk).first()
        if shop is None:
            return Response(
                {"detail": "Boutique introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not (_is_admin(request.user) or shop.pk == request.user.pk):
            return Response(
                {"detail": "Action non autorisée."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if "name" in request.data:
            shop.shop_name = (request.data.get("name") or "").strip()
        if "description" in request.data:
            shop.shop_description = request.data.get("description") or ""

        category = request.data.get("category")
        if category not in (None, ""):
            category_name = str(category)
            cat = (
                Category.objects.filter(name__iexact=category_name).first()
                or Category.objects.filter(name__icontains=category_name).first()
            )
            if cat is not None:
                shop.shop_category = cat

        image = request.FILES.get("shop_image")
        if image is not None:
            shop.shop_image = image

        shop.save()
        return Response(self.get_serializer(shop).data)


def _is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.role in ("admin", "superadmin")
    )


class BoutiqueRequestViewSet(viewsets.ModelViewSet):
    """Demandes de location d'espace vendeur (/louer-espace).

    - create / my-request : accessibles à l'utilisateur connecté
    - list / detail / validate / reject / pending-count : réservés aux admins
    """

    serializer_class = BoutiqueRequestSerializer
    pagination_class = AdminPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    OPEN_STATUSES = (BoutiqueRequest.Status.PENDING, BoutiqueRequest.Status.VALIDATED)
    ADMIN_ACTIONS = (
        "list",
        "retrieve",
        "validate",
        "reject",
        "pending_count",
        "update",
        "partial_update",
        "destroy",
    )

    def get_permissions(self):
        if self.action in self.ADMIN_ACTIONS:
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        qs = BoutiqueRequest.objects.select_related("owner").all()
        if not _is_admin(self.request.user):
            qs = qs.filter(owner=self.request.user)
        status = self.request.query_params.get("status")
        search = self.request.query_params.get("search")
        if status and status != "all":
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(company_name__icontains=search)
                | Q(owner_name__icontains=search)
                | Q(province__icontains=search)
                | Q(commune__icontains=search)
            )
        return qs

    def create(self, request, *args, **kwargs):
        if BoutiqueRequest.objects.filter(
            owner=request.user, status__in=self.OPEN_STATUSES
        ).exists():
            return Response(
                {"detail": "Une demande de location est déjà en cours."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        from admin.models import PlatformSettings
        from notification.models import Notification
        from users.models import User

        boutique = serializer.save(owner=self.request.user)
        settings = PlatformSettings.load()
        require_approval = settings.moderation.get(
            "requireShopApproval", False
        )
        if require_approval and settings.notifications.get("newShopPending", False):
            admins = User.objects.filter(role__in=("admin", "superadmin"))
            Notification.objects.bulk_create([
                Notification(
                    user=admin,
                    title="Nouvelle demande de boutique",
                    message=f"La demande de boutique « {boutique.company_name} » attend une validation.",
                    type=Notification.Type.SHOP,
                )
                for admin in admins
            ])
        elif not require_approval:
            boutique.status = BoutiqueRequest.Status.VALIDATED
            boutique.save(update_fields=["status"])
            self._activate_shop_owner(boutique)

    @staticmethod
    def _activate_shop_owner(boutique):
        owner = boutique.owner
        owner.role = User.Role.SELLER
        owner.is_active = True
        owner.shop_status = User.ShopStatus.VALIDATED
        if boutique.company_name:
            owner.shop_name = boutique.company_name
        if boutique.phone:
            owner.phone = boutique.phone
        elif boutique.whatsapp:
            owner.phone = boutique.whatsapp
        if boutique.slogan:
            owner.shop_description = boutique.slogan
        if boutique.industry:
            category = Category.objects.filter(name__iexact=boutique.industry).first()
            if category is None:
                category = Category.objects.filter(
                    name__icontains=boutique.industry
                ).first()
            if category is not None:
                owner.shop_category = category
        owner.save()

    @action(detail=False, methods=["get"], url_path="my-request")
    def my_request(self, request):
        boutique = (
            BoutiqueRequest.objects.filter(owner=request.user)
            .order_by("-created_at")
            .first()
        )
        if boutique is None:
            return Response({"exists": False, "status": None, "boutique": None})
        return Response(
            {
                "exists": True,
                "status": boutique.status,
                "boutique": self.get_serializer(boutique).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="pending-count")
    def pending_count(self, request):
        count = BoutiqueRequest.objects.filter(
            status=BoutiqueRequest.Status.PENDING
        ).count()
        return Response({"count": count})

    @action(detail=True, methods=["patch"], url_path="validate")
    def validate(self, request, pk=None):
        boutique = self.get_object()
        boutique.status = BoutiqueRequest.Status.VALIDATED
        boutique.save(update_fields=["status"])
        self._activate_shop_owner(boutique)
        owner = boutique.owner

        # Retourner aussi les infos utilisateur mises à jour pour que le front puisse rafraîchir la session
        from users.serializer import UserSerializer
        user_data = UserSerializer(owner, context={"request": request}).data
        return Response({
            "boutique": self.get_serializer(boutique).data,
            "user": user_data,
        })

    @action(detail=True, methods=["patch"], url_path="reject")
    def reject(self, request, pk=None):
        boutique = self.get_object()
        boutique.status = BoutiqueRequest.Status.REJECTED
        boutique.save(update_fields=["status"])
        return Response(self.get_serializer(boutique).data)

from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from .models import Product, ProductImage
from rest_framework import viewsets, status
from rest_framework.decorators import action
from .serializers import ProductSerializer, ProductImageSerializer
from admin.pagination import AdminPageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.permisions import IsProductOwnerOrAdmin, IsSellerOrAdmin
from rest_framework.parsers import MultiPartParser, FormParser

# Create your views here.
class ProductPagination(AdminPageNumberPagination):
    page_size = 100
    page_size_query_param = "perPage"
    max_page_size = 1000

class ProductsView(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("name")
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    ordering = "name"

    def get_queryset(self):
        qs = super().get_queryset().select_related("owner", "category").prefetch_related("images")
        user = self.request.user
        is_admin = user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "superadmin")
        )
        if not is_admin:
            # Catalogue public : uniquement les produits actifs. Un vendeur
            # voit en plus ses propres produits, quel que soit leur statut.
            if user.is_authenticated:
                qs = qs.filter(Q(status=Product.Status.ACTIVE) | Q(owner=user))
            else:
                qs = qs.filter(status=Product.Status.ACTIVE)
        search = self.request.query_params.get("search")
        status_param = self.request.query_params.get("status")
        owner = self.request.query_params.get("owner")
        shop = self.request.query_params.get("shop")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(details__icontains=search))
        if status_param:
            qs = qs.filter(status=status_param)
        # Support pour les deux paramètres : owner (ID utilisateur) et shop (ID boutique)
        if owner and str(owner).isdigit():
            qs = qs.filter(owner_id=int(owner))
        elif shop and str(shop).isdigit():
            # Pour compatibilité avec l'ancien paramètre "shop"
            qs = qs.filter(owner_id=int(shop))
        return qs

    def perform_create(self, serializer):
        # Vérifier les paramètres de modération
        from admin.models import PlatformSettings
        settings = PlatformSettings.load()
        require_approval = settings.moderation.get("requireProductApproval", False)
        
        # Si l'approbation est requête, le produit est créé en statut INACTIVE
        # et une demande de publication est créée
        status = Product.Status.INACTIVE if require_approval else Product.Status.ACTIVE
        # Le propriétaire est toujours l'utilisateur connecté, pas celui du payload
        product = serializer.save(owner=self.request.user, status=status)
        
        if require_approval:
            from publications.models import PublicationRequest
            PublicationRequest.objects.create(
                product=product,
                seller=self.request.user,
                status=PublicationRequest.Status.PENDING
            )
        return serializer

    def create(self, request, *args, **kwargs):
        """Crée un produit avec ses photos (obligatoires) en une seule requête.

        Le front envoie un ``FormData`` : champs du produit + ``images`` (une ou
        plusieurs). Un produit doit avoir au moins une photo pour être publié.
        """
        images = request.FILES.getlist("images")
        if not images:
            return Response(
                {"images": ["Au moins une photo du produit est obligatoire."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Utiliser perform_create pour gérer la modération
        self.perform_create(serializer)
        product = serializer.instance

        for index, image in enumerate(images):
            ProductImage.objects.create(
                product=product, image=image, is_main=(index == 0)
            )

        return Response(
            self.get_serializer(product).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views += 1
        instance.save(update_fields=["views"])
        return super().retrieve(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            # Catalogue public : vitrine accessible à tous (visiteurs compris).
            # La visibilité se limite aux produits actifs (voir get_queryset).
            permission_classes = [AllowAny]
        elif self.action in (
            "destroy",
            "update",
            "partial_update",
            "set_status",
            "upload_images",
            "remove_image",
        ):
            # Proprietaire du produit ou administrateur (verifie sur l'objet).
            permission_classes = [IsProductOwnerOrAdmin]
        elif self.action == "create":
            # Seuls les vendeurs et les administrateurs publient des produits.
            permission_classes = [IsSellerOrAdmin]
        else:
            # my_products, my_stats
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["get"], url_path="my-products")
    def my_products(self, request):
        """Produits du vendeur connecté (tous statuts confondus)."""
        qs = (
            Product.objects.filter(owner=request.user)
            .select_related("owner", "category")
            .prefetch_related("images")
            .order_by("-created_at")
        )
        search = request.query_params.get("search")
        status_param = request.query_params.get("status")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(details__icontains=search))
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="my-stats")
    def my_stats(self, request):
        """Indicateurs du tableau de bord vendeur."""
        products = Product.objects.filter(owner=request.user)
        total_products = products.count()
        active_products = products.filter(status=Product.Status.ACTIVE).count()
        total_views = products.aggregate(total=Sum("views"))["total"] or 0

        since = timezone.now() - timedelta(days=7)
        subtotal = ExpressionWrapper(
            F("price") * F("quantity"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        from commande.models import OrderItem

        weekly_sales = (
            OrderItem.objects.filter(
                product__owner=request.user,
                order__created_at__gte=since,
            )
            .exclude(order__status="cancelled")
            .aggregate(total=Sum(subtotal))["total"]
        )

        return Response(
            {
                "total_products": total_products,
                "active_products": active_products,
                "total_views": total_views,
                "weekly_sales": int(weekly_sales or 0),
            }
        )

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        product = self.get_object()
        new_status = request.data.get("status", product.status)
        if new_status == Product.Status.ACTIVE and not product.images.exists():
            return Response(
                {"detail": "Ajoutez au moins une photo avant de publier ce produit."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_status == Product.Status.ACTIVE and product.stock <= 0:
            return Response(
                {"detail": "Impossible de publier un produit en rupture de stock. Ajoutez du stock d'abord."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product.status = new_status
        product.save()
        return Response(self.get_serializer(product).data)

    @action(detail=True, methods=["post"], url_path="images", parser_classes=[MultiPartParser, FormParser])
    def upload_images(self, request, pk=None):
        product = self.get_object()
        files = request.FILES.getlist("images")
        is_main_flag = request.data.get("is_main", "true").lower() == "true"
        if not files:
            return Response({"detail": "Aucune image envoyée."}, status=400)

        created = []
        for i, f in enumerate(files):
            img = ProductImage.objects.create(
                product=product,
                image=f,
                is_main=(i == 0 and is_main_flag),
            )
            created.append(img)

        return Response(
            ProductImageSerializer(created, many=True, context={"request": request}).data,
            status=201,
        )

    @action(detail=True, methods=["delete"], url_path="images/(?P<image_id>[\\d]+)")
    def remove_image(self, request, pk=None, image_id=None):
        product = self.get_object()
        img = ProductImage.objects.filter(product=product, id=image_id).first()
        if not img:
            return Response({"detail": "Image introuvable."}, status=404)
        if product.images.count() <= 1:
            return Response(
                {"detail": "Un produit doit conserver au moins une photo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        img.image.delete(save=False)
        img.delete()
        return Response(status=204)
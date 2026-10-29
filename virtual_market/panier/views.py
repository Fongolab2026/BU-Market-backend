from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from commande.models import Order, OrderItem
from commande.serializers import OrderSerializer
from products.models import Product

from .models import Cart, CartItem
from .serializers import AddToCartSerializer, CartItemSerializer, CartSerializer


def _clean_cart_out_of_stock(cart):
    """Supprime les articles du panier dont le stock est à 0."""
    out_of_stock_items = cart.items.filter(product__stock=0)
    count = out_of_stock_items.count()
    if count > 0:
        out_of_stock_items.delete()
    return count


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _get_or_create_cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    @action(detail=False, methods=["post"], url_path="add-item")
    def add_item(self, request):
        """Ajoute un produit au panier, ou augmente sa quantité s'il y est déjà."""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
            cart = Cart.objects.select_for_update().get_or_create(user=request.user)[0]
            product = Product.objects.select_for_update().get(pk=product.pk)
            if product.status != Product.Status.ACTIVE:
                raise ValidationError({"detail": "Ce produit n'est plus disponible."})
            if (
                not product.owner.is_active
                or (
                    product.owner.role == "seller"
                    and product.owner.shop_status != "validated"
                )
            ):
                raise ValidationError({"detail": "Le vendeur de ce produit n'est pas disponible."})

            item = CartItem.objects.select_for_update().filter(cart=cart, product=product).first()
            new_quantity = (item.quantity if item else 0) + quantity
            if product.stock <= 0:
                raise ValidationError({"quantity": ["Ce produit est en rupture de stock."]})
            if new_quantity > product.stock:
                raise ValidationError(
                    {"quantity": [f"Stock insuffisant. Disponible : {product.stock}."]}
                )

            if item is None:
                CartItem.objects.create(cart=cart, product=product, quantity=new_quantity)
            else:
                item.quantity = new_quantity
                item.save(update_fields=["quantity"])

        # Nettoyer le panier des produits en rupture
        removed_count = _clean_cart_out_of_stock(cart)
        
        # Retourner le panier mis à jour avec le total
        cart_data = CartSerializer(cart).data
        cart_data["removed_out_of_stock"] = removed_count
        return Response(cart_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        """Transforme le panier courant en commande, décrémente le stock puis vide le panier."""
        with transaction.atomic():
            cart = Cart.objects.select_for_update().filter(user=request.user).first()
            if cart is None:
                raise ValidationError({"cart": ["Votre panier est vide."]})
            items = list(
                cart.items.select_for_update().select_related("product__owner").all()
            )
            if not items:
                raise ValidationError({"cart": ["Votre panier est vide."]})

            # Lock and re-read stock inside the transaction so concurrent
            # checkouts cannot both sell the same remaining units.
            products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(
                    pk__in=[item.product_id for item in items]
                )
            }
            for item in items:
                product = products[item.product_id]
                if product.status != Product.Status.ACTIVE:
                    raise ValidationError(
                        {"cart": [f"Le produit « {product.name} » n'est plus disponible."]}
                    )
                if (
                    not product.owner.is_active
                    or (
                        product.owner.role == "seller"
                        and product.owner.shop_status != "validated"
                    )
                ):
                    raise ValidationError(
                        {"cart": [f"Le vendeur de « {product.name} » n'est plus disponible."]}
                    )
                if item.quantity > product.stock:
                    raise ValidationError(
                        {"cart": [
                            f"Stock insuffisant pour « {product.name} » "
                            f"(disponible : {product.stock})."
                        ]}
                    )

            order = Order.objects.create(user=request.user)
            for item in items:
                product = products[item.product_id]
                images = list(product.images.all())
                main_image = next((image for image in images if image.is_main), None)
                if main_image is None and images:
                    main_image = images[0]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    seller=product.owner,
                    product_name=product.name,
                    shop_name=product.owner.shop_display_name,
                    product_image_key=main_image.image.name if main_image else "",
                    quantity=item.quantity,
                    price=product.price,
                )
                product.stock -= item.quantity
                product.save(update_fields=["stock"])
            cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="sync-stock")
    def sync_stock(self, request):
        """Synchronise le panier avec les stocks actuels (supprime les articles en rupture)."""
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response({"items": [], "total_prices": 0, "removed_out_of_stock": 0})
        
        removed_count = _clean_cart_out_of_stock(cart)
        cart_data = CartSerializer(cart).data
        cart_data["removed_out_of_stock"] = removed_count
        return Response(cart_data)

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """Récupère le panier actuel de l'utilisateur (créé si inexistant)."""
        cart = self._get_or_create_cart()
        # Nettoyer les articles en rupture de stock
        _clean_cart_out_of_stock(cart)
        return Response(CartSerializer(cart).data)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user).order_by("-added_at")

    def get_permissions(self):
        # Allow all authenticated users to perform actions on their own cart items
        # The queryset filtering ensures they only see their own items
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        product = serializer.validated_data["product"]
        if CartItem.objects.filter(cart=cart, product=product).exists():
            raise ValidationError(
                {"product": "Ce produit est déjà dans le panier. Utilisez add-item pour ajuster la quantité."}
            )
        serializer.save(cart=cart)

    def perform_update(self, serializer):
        """Vérifie le stock lors de la mise à jour de quantité."""
        product = serializer.instance.product
        new_quantity = serializer.validated_data.get("quantity", serializer.instance.quantity)
        if new_quantity > product.stock:
            raise ValidationError(
                {"quantity": [f"Stock insuffisant. Disponible : {product.stock}."]}
            )
        serializer.save()
        
        # Nettoyer si stock à 0 après mise à jour
        cart = serializer.instance.cart
        _clean_cart_out_of_stock(cart)

    def destroy(self, request, *args, **kwargs):
        """Supprime un article du panier."""
        instance = self.get_object()
        # Vérifier que l'article appartient bien au panier de l'utilisateur
        if instance.cart.user != request.user:
            raise PermissionDenied("Cet article ne vous appartient pas.")
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

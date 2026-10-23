from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from commande.models import Order, OrderItem
from commande.serializers import OrderSerializer
from notification.models import Notification
from products.models import Product

from .models import Cart, CartItem
from .serializers import AddToCartSerializer, CartItemSerializer, CartSerializer


def _notify_seller_out_of_stock(product):
    """Notifie le vendeur quand son produit tombe en rupture de stock."""
    if product.owner:
        Notification.objects.create(
            user=product.owner,
            title="Rupture de stock",
            message=f"Votre produit « {product.name} » est en rupture de stock.",
            type=Notification.Type.ALERT,
        )


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

        if product.status != Product.Status.ACTIVE:
            raise ValidationError({"detail": "Ce produit n'est plus disponible."})

        cart = self._get_or_create_cart()
        item = CartItem.objects.filter(cart=cart, product=product).first()
        new_quantity = (item.quantity if item else 0) + quantity

        if product.stock <= 0:
            raise ValidationError(
                {"quantity": ["Ce produit est en rupture de stock."]}
            )
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
        cart = Cart.objects.filter(user=request.user).first()
        items = list(cart.items.select_related("product").all()) if cart else []

        if not items:
            raise ValidationError({"cart": ["Votre panier est vide."]})

        # On valide tout le panier avant toute écriture pour rester cohérent.
        for item in items:
            product = item.product
            if product.status != Product.Status.ACTIVE:
                raise ValidationError(
                    {"cart": [f"Le produit « {product.name} » n'est plus disponible."]}
                )
            if item.quantity > product.stock:
                raise ValidationError(
                    {
                        "cart": [
                            f"Stock insuffisant pour « {product.name} » "
                            f"(disponible : {product.stock})."
                        ]
                    }
                )

        with transaction.atomic():
            order = Order.objects.create(user=request.user)
            for item in items:
                product = item.product
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.price,
                )
                old_stock = product.stock
                product.stock -= item.quantity
                product.save(update_fields=["stock"])
                
                # Notifier le vendeur si le stock tombe à 0
                if old_stock > 0 and product.stock <= 0:
                    _notify_seller_out_of_stock(product)
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
        cart = serializer.validated_data.get("cart")
        if cart is not None and cart.user != self.request.user:
            raise PermissionDenied("Ce panier ne vous appartient pas.")
        serializer.save()

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

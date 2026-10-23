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

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

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
                product.stock -= item.quantity
                product.save(update_fields=["stock"])
            cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user).order_by("-added_at")

    def perform_create(self, serializer):
        cart = serializer.validated_data.get("cart")
        if cart is not None and cart.user != self.request.user:
            raise PermissionDenied("Ce panier ne vous appartient pas.")
        serializer.save()

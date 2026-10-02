from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from commande.models import Order, OrderItem
from commande.serializers import OrderSerializer
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="add-item")
    def add_item(self, request):
        product_id = request.data.get("product")
        try:
            quantity = int(request.data.get("quantity", 1))
        except (TypeError, ValueError):
            raise ValidationError({"quantity": "La quantité doit être un nombre entier."})
        if not product_id:
            raise ValidationError({"product": "Le produit est obligatoire."})
        if quantity < 1:
            raise ValidationError({"quantity": "La quantité doit être supérieure à zéro."})

        from products.models import Product
        product = Product.objects.filter(id=product_id, status=Product.Status.ACTIVE).first()
        if product is None:
            raise ValidationError({"product": "Ce produit n'est pas disponible."})
        if quantity > product.stock:
            raise ValidationError({"quantity": "La quantité demandée dépasse le stock disponible."})

        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        next_quantity = quantity if created else item.quantity + quantity
        if next_quantity > product.stock:
            raise ValidationError({"quantity": "La quantité totale dépasse le stock disponible."})
        item.quantity = next_quantity
        item.save(update_fields=["quantity"])
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = list(cart.items.select_related("product"))
        if not items:
            raise ValidationError({"cart": "Votre panier est vide."})

        with transaction.atomic():
            for item in items:
                if item.product.status != item.product.Status.ACTIVE or item.quantity > item.product.stock:
                    raise ValidationError({"cart": f"Le produit {item.product.name} n'est plus disponible en quantité suffisante."})
            order = Order.objects.create(user=request.user)
            OrderItem.objects.bulk_create([
                OrderItem(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
                for item in items
            ])
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
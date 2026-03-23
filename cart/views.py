from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Cart, CartItem
from products.models import Product
from .serializers import CartSerializer

# api/cart/ Savatcha
class CartView(APIView):
    permission_classes = [IsAuthenticated]
    # get savatni ko'rish
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)
    #  post product qo'shish,
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product')
        quantity = request.data.get('quantity', 1)
        if not product_id:
            return Response({"error": "product required"}, status=400)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "product not found"}, status=404)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )
        if not created:
            item.quantity += int(quantity)
        else:
            item.quantity = int(quantity)
        item.save()
        return Response({"message": "Product added to cart"}, status=200)
    # product-item_id ni sonini o'zgartirish
    def put(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity'))
        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"error": "item not found"}, status=404)
        if quantity <= 0:
            item.delete()
            return Response({"message": "Item deleted"})
        item.quantity = quantity
        item.save()
        return Response({"message": "Quantity updated"})
    #  product yani itemni o'chirish
    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item_id = request.data.get('item_id')
        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"error": "item not found"}, status=404)
        item.delete()
        return Response({"message": "Item deleted"})

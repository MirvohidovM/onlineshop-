from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from cart.models import Cart
from .models import Order, OrderItem, StripeSessionMap
from .serializers import OrderSerializer
import stripe
import json
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


stripe.api_key = settings.STRIPE_SECRET_KEY

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.get(user=request.user)
        items = cart.items.all()

        if not items:
            return Response({"error": "Cart is empty"}, status=400)

        order = Order.objects.create(user=request.user)

        total_price = 0

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            total_price += item.product.price * item.quantity

        order.total_price = total_price
        order.save()

        items.delete()

        return Response({
            "message": "Order confirmed successfully",
            "order_id": order.id,
            "total_price": order.total_price
        })

class UserOrdersView(ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-id')


class StripeCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='payment',
            metadata = {
                "order_id": str(order_id)
            },
            success_url='http://localhost:3000/success',
            cancel_url='http://localhost:3000/cancel',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f'Order #{order.id}'},
                    'unit_amount': int(order.total_price * 100),
                },
                'quantity': 1,
            }],
        )
        StripeSessionMap.objects.create(
            session_id=session.id,
            order=order
        )
        print("✅ Created session:", session.id)
        return Response({"checkout_url": session.url})

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    try:
        event = json.loads(payload)
    except:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session['metadata'].get('order_id')
        try:
            order = Order.objects.get(id=order_id)
            order.status = 'paid'
            order.save()
        except Order.DoesNotExist:
            pass
    return HttpResponse(status=200)


class StripeSuccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')

        order = Order.objects.get(id=order_id, user=request.user)
        order.status = 'paid'
        order.save()

        return Response({"message": "Payment confirmed"})
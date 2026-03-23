from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from cart.models import Cart
from .models import Order, OrderItem, StripeSessionMap
from .serializers import OrderSerializer
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


# api/checkout/ savatchadagilarni buyurtmaga o'tkazish
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

        # 🔥 cartni tozalaymiz
        items.delete()

        return Response({
            "message": "Order confirmed successfully",
            "order_id": order.id,
            "total_price": order.total_price
        })

# get api/orders : buyurtmalarni ko'rish
class UserOrdersView(ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-id')

# api/pay/ Buyurtmani to'lash: Fake Payment
class PayOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "order not found"}, status=404)

        if order.status != 'pending':
            return Response({"error": "already paid or delivered"}, status=400)

        # 🔥 fake payment
        order.status = 'paid'
        order.save()

        return Response({
            "message": "Payment successful",
            "order_id": order.id,
            "status": order.status
        })


# api/stripe/checkout/ Buyurtmani to'lash: Stripe
# views.py

stripe.api_key = settings.STRIPE_SECRET_KEY

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

        # 🔑 ENG MUHIM QATOR
        StripeSessionMap.objects.create(
            session_id=session.id,
            order=order
        )

        print("✅ Created session:", session.id)

        return Response({"checkout_url": session.url})

# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
#     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
#
#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
#     except stripe.error.SignatureVerificationError:
#         return HttpResponse(status=400)
#     except Exception:
#         return HttpResponse(status=400)
#
#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']
#         order_id = session['metadata'].get('order_id')
#         try:
#             order = Order.objects.get(id=order_id)
#             order.status = 'paid'
#             order.save()
#         except Order.DoesNotExist:
#             pass
#
#     return HttpResponse(status=200)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        print("✅ Event:", event['type'])
    except Exception as e:
        print("❌ Error:", e)
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session['id']

        print("➡ Session ID:", session_id)

        try:
            mapping = StripeSessionMap.objects.get(session_id=session_id)
            order = mapping.order

            order.status = 'paid'
            order.save()

            print("✅ Order updated:", order.id)

        except StripeSessionMap.DoesNotExist:
            print("❌ Mapping not found")

    return HttpResponse(status=200)

# Success_Url: api/stripe/success/ Buyurtma statusini "to'landi"ga o'zgartirish
class StripeSuccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')

        order = Order.objects.get(id=order_id, user=request.user)
        order.status = 'paid'
        order.save()

        return Response({"message": "Payment confirmed"})
from django.urls import path
from .views import CheckoutView, UserOrdersView, PayOrderView,StripeCheckoutView, StripeSuccessView, stripe_webhook

urlpatterns = [
    path('checkout/', CheckoutView.as_view()),
    path('orders/', UserOrdersView.as_view()),
    path('pay/', PayOrderView.as_view()),
    path('stripe/checkout/', StripeCheckoutView.as_view()),
    path('stripe/success/', StripeSuccessView.as_view()),
    path('stripe/webhook/', stripe_webhook),
]
from django.urls import path
from .views import Checkout , payment_success, payment_cancel

urlpatterns = [
    path("<int:reservation_pk>/", Checkout.as_view(), name="checkout"),
    path("success/<int:reservation_pk>/", payment_success, name="payment_success"),
    path("cancel/<int:reservation_pk>/", payment_cancel, name="payment_cancel"),
]

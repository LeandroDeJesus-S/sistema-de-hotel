from django.urls import path
from .views import Payment, payment_success, payment_cancel

urlpatterns = [
    path("<int:room_id>-<int:client_id>", Payment.as_view(), name="payment"),
    path("payment_success", payment_success, name="payment_success"),
    path("payment_cancel", payment_cancel, name="payment_cancel"),
]

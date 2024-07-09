from django.urls import path
from .views import *

urlpatterns = [
    path("pre-reserva", PreReserva.as_view(), name="pre_reserva"),
    path("reserva", ListRooms.as_view(), name="reserva"),
]
# /<int:client_id>-<int:reservation_id>-<int:room_class_id>
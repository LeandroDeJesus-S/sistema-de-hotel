from django.urls import path
from .views import Quartos

urlpatterns = [
    path("quartos/", Quartos.as_view(), name="quartos"),
#     path("pre-reserva", PreReserva.as_view(), name="pre_reserva"),
#     path("reserva", ListaQuartos.as_view(), name="reserva"),
]

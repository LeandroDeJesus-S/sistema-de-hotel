from django.urls import path
from .views import *

urlpatterns = [
    path("pre-reserva", PreReserva.as_view(), name="pre_reserva"),
    path("reserva", ListaQuartos.as_view(), name="reserva"),
    path("acomodacoes", Acomodacoes.as_view(), name="acomodacoes"),
]

from django.urls import path
from .views import Quartos, QuartoDetail, Reservar

urlpatterns = [
    path("quartos/", Quartos.as_view(), name="quartos"),
    path("<int:pk>/", QuartoDetail.as_view(), name="quarto"),
    path("reserva/<int:quarto_pk>/", Reservar.as_view(), name="reserva"),
]

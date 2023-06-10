from django.urls import path
from .views import *

urlpatterns = [
    path("", Reserva.as_view(), name="reserva"),
]

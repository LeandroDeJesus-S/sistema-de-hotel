from django.urls import path
from .views import Agendar, agendamento_success

urlpatterns = [
    path("<int:quarto_pk>/", Agendar.as_view(), name="agendar"),
    path("<int:reservation_pk>/success/", agendamento_success, name="agendamento_success"),
]

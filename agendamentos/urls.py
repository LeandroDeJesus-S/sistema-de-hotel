from django.urls import path
from .views import Agendar

urlpatterns = [
    path("<int:quarto_pk>/", Agendar.as_view(), name="agendar"),
]

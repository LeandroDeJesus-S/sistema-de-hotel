from django.urls import path
from .views import Cliente

urlpatterns = [
    path('', Cliente.as_view(), name='cliente'),
] 

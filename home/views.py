from django.shortcuts import render
from django.db.models.aggregates import Count
from reservas.models import Beneficio, Reserva, Quarto
from home.models import Hotel
from restaurantes.models import Restaurant

def home(request):
    context = {
        'beneficios': Beneficio.objects.filter(displayable_on_homepage=True)
    }
    top4_rooms = Reserva.objects.filter(status__in=['F', 'A']).values('quarto').annotate(
        room_count=Count('quarto')
    ).order_by('-room_count').values('quarto')[:3]
    
    context['quartos'] = Quarto.objects.filter(pk__in=top4_rooms)
    context['restaurante'] = Restaurant.objects.first()
    return render(request, 'static/home/html/home.html', context)

from django.shortcuts import render
from django.db.models.aggregates import Count
from reservations.models import Benefit, Reservation, Room
from restaurants.models import Restaurant

def home(request):
    context = {
        'benefits': Benefit.objects.filter(displayable_on_homepage=True)
    }
    top4_rooms = Reservation.objects.filter(status__in=['F', 'A']).values('room').annotate(
        room_count=Count('room')
    ).order_by('-room_count').values('room')[:3]
    
    context['rooms'] = Room.objects.filter(pk__in=top4_rooms)
    context['restaurant'] = Restaurant.objects.first()
    return render(request, 'static/home/html/home.html', context)

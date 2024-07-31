import logging
from django.shortcuts import render
from django.db.models.aggregates import Count
from reservations.models import Benefit, Reservation, Room
from restaurants.models import Restaurant
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    logger = logging.getLogger('djangoLogger')

    context = {
        'benefits': Benefit.objects.filter(displayable_on_homepage=True)
    }
    top4_rooms = Reservation.objects.filter(status__in=['F', 'A']).values('room').annotate(
        room_count=Count('room')
    ).order_by('-room_count').values('room')[:3]
    logger.info(f'top 4 rooms fetched: {top4_rooms}')

    context['rooms'] = Room.objects.filter(pk__in=top4_rooms)
    context['restaurant'] = Restaurant.objects.first()
    logger.debug(f'rendering home with context {context}')
    return render(request, 'static/home/html/home.html', context)

import logging
from django.shortcuts import render
from django.db.models.aggregates import Count
from reservations.models import Benefit, Reservation, Room
from services.models import Service
from django.views.decorators.http import require_GET
from django.http import HttpRequest


@require_GET
def home(request: HttpRequest):
    logger = logging.getLogger('djangoLogger')

    context = {
        'benefits': Benefit.objects.filter(displayable_on_homepage=True)
    }
    top4_rooms = Reservation.objects.filter(status__in=['F', 'A', 'S']).values('room').annotate(
        room_count=Count('room')
    ).order_by('-room_count').values('room')[:4]
    logger.info(f'top 4 rooms fetched: {top4_rooms}')

    context['rooms'] = Room.objects.filter(pk__in=top4_rooms)
    context['services'] = Service.objects.filter(hotel__pk=1)
    logger.debug(f'rendering home with context {context}')
    return render(request, 'static/home/html/home.html', context)

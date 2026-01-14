from django.db.models.aggregates import Count
from django.http import HttpRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET

from reservations.models import Benefit, Reservation, Room
from services.models import Service


@require_GET
def home(request: HttpRequest):
    """Renders the homepage with benefits, top rooms, and services.
    Args:
        request (HttpRequest): The HTTP request object.
    Returns:
        HttpResponse: The rendered homepage.
    """
    context = {'benefits': Benefit.objects.filter(displayable_on_homepage=True)}
    top4_rooms = (
        Reservation.objects.filter(status__in=['F', 'A', 'S'])
        .values('room')
        .annotate(room_count=Count('room'))
        .order_by('-room_count')
        .values('room')[:4]
    )

    context['rooms'] = Room.objects.filter(pk__in=top4_rooms)
    context['services'] = Service.objects.filter(hotel__pk=1)
    return render(request, 'static/home/html/home.html', context)

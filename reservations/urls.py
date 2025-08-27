from django.urls import include, path

from .views import (
    ReservationHistory,
    ReservationsHistory,
    Reserve,
    RoomDetail,
    Rooms,
)

urlpatterns = [
    path(
        'quartos/',
        include([
            path('', Rooms.as_view(), name='rooms'),
            path('<int:pk>/', RoomDetail.as_view(), name='room'),
            path('<int:room_pk>/reservar', Reserve.as_view(), name='reserve'),
        ]),
    ),
    path(
        'minhas-reservas/',
        include([
            path('', ReservationsHistory.as_view(), name='reservations_history'),
            path(
                '<int:pk>/',
                ReservationHistory.as_view(),
                name='reservation_history',
            ),
        ]),
    ),
]

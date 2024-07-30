from django.urls import path
from .views import Rooms, RoomDetail, Reserve, ReservationsHistory, ReservationHistory

urlpatterns = [
    path("quartos/", Rooms.as_view(), name="rooms"),
    path("<int:pk>/", RoomDetail.as_view(), name="room"),
    path("reserva/<int:room_pk>/", Reserve.as_view(), name="reserve"),
    path("minhas-reservas/", ReservationsHistory.as_view(), name="reservations_history"),
    path("minhas-reservas/<int:pk>", ReservationHistory.as_view(), name="reservation_history"),
]

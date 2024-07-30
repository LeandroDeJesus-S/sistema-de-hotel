from django.urls import path
from .views import Schedules, schedule_success

urlpatterns = [
    path("<int:room_pk>/", Schedules.as_view(), name="schedule"),
    path("<int:reservation_pk>/success/", schedule_success, name="schedule_success"),
]

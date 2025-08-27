from django.contrib import admin

from utils import support

from .models import Scheduling


class AgendamentoAdmin(admin.ModelAdmin):
    model = Scheduling
    list_display = ('client', 'date', 'room')

    @admin.display(description='Data')
    def date(self, obj: Scheduling):  # noqa: PLR6301
        in_ = support.fmt_date(obj.reservation.checkin)
        out = support.fmt_date(obj.reservation.checkout)
        return f'{in_} - {out}'

    @admin.display(description='Quarto')
    def room(self, obj):  # noqa: PLR6301
        return f'Quarto {obj.reservation.room.number}'


admin.site.register(Scheduling, AgendamentoAdmin)

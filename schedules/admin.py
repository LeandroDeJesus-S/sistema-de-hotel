from django.contrib import admin
from .models import Scheduling
from utils import support


class AgendamentoAdmin(admin.ModelAdmin):
    model = Scheduling
    list_display = ('client', 'date', 'room')

    @admin.display(description='Data')
    def date(self, obj: Scheduling):
        in_ = support.fmt_date(obj.reservation.checkin)
        out = support.fmt_date(obj.reservation.checkout)
        return f'{in_} - {out}'
    
    @admin.display(description='Quarto')
    def room(self, obj):
        return f'Quarto {obj.reservation.room.number}'
    

admin.site.register(Scheduling, AgendamentoAdmin)

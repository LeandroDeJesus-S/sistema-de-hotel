from django.contrib import admin
from .models import Agendamento


class AgendamentoAdmin(admin.ModelAdmin):
    model = Agendamento
    exclude = ()

admin.site.register(Agendamento, AgendamentoAdmin)

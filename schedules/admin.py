from django.contrib import admin
from .models import Scheduling


class AgendamentoAdmin(admin.ModelAdmin):
    model = Scheduling
    exclude = ()

admin.site.register(Scheduling, AgendamentoAdmin)

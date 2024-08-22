from django.contrib import admin
from .models import Service


class RestaurantAdmin(admin.ModelAdmin):
    model = Service
    exclude = ()
    list_filter = [
        'hotel'
    ]


admin.site.register(Service, RestaurantAdmin)

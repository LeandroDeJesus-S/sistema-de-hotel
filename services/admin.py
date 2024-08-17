from django.contrib import admin
from .models import Services


class RestaurantAdmin(admin.ModelAdmin):
    model = Services
    exclude = ()
    list_filter = [
        'hotel'
    ]


admin.site.register(Services, RestaurantAdmin)

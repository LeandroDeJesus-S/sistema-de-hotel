from django.contrib import admin
from .models import Restaurant


class RestaurantAdmin(admin.ModelAdmin):
    model = Restaurant
    exclude = ()
    list_filter = [
        'hotel'
    ]


admin.site.register(Restaurant, RestaurantAdmin)

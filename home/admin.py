from django.contrib import admin
from .models import Hotel, Contact


class HotelAdmin(admin.ModelAdmin):
    model = Hotel
    exclude = ()
    search_fields = [
        'name'
    ]


class ContactAdmin(admin.ModelAdmin):
    model = Contact
    exclude = ()
    list_display = [
        'hotel', 'email', 'phone',
    ]
    list_filter = [
        'hotel'
    ]
    search_fields = [
        'hotel', 'email', 'telefone'
    ]

admin.site.register(Hotel, HotelAdmin)
admin.site.register(Contact, ContactAdmin)

from django.contrib import admin

from .models import ContactChannel, Hotel


class HotelAdmin(admin.ModelAdmin):
    model = Hotel
    exclude = ()
    search_fields = ['name']


class ContactChannelAdmin(admin.ModelAdmin):
    model = ContactChannel
    exclude = ()
    list_display = [
        'hotel',
        'display_name',
        'display_value',
        'active',
    ]
    list_filter = ['hotel', 'active']
    search_fields = ['hotel__name', 'display_name', 'display_value']


admin.site.register(Hotel, HotelAdmin)
admin.site.register(ContactChannel, ContactChannelAdmin)

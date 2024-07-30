from django.contrib import admin
from .models import Benefit, Class, Room, Reservation


class BenefitAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'short_desc',
        'displayable_on_homepage',
    ]
    list_editable = [
        'displayable_on_homepage',
    ]


class ClassAdmin(admin.ModelAdmin):
    list_display = [
        'name',
    ]


class RoomAdmin(admin.ModelAdmin):
    list_display = [
        'room_class',
        'number',
        'adult_capacity',
        'child_capacity',
        'daily_price_formatted',
        'available',
        'image'
    ]
    list_filter = ['hotel']
    list_editable = ['available']


@admin.display(description='Status')
def status(obj):
    return obj.get_status_display().title()

class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'client',
        'room',
        'checkin',
        'checkout',
        'active',
        status,
    ]
    
admin.site.register(Benefit, BenefitAdmin)
admin.site.register(Class, ClassAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(Reservation, ReservationAdmin)
 
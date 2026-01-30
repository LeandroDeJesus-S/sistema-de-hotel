from django.contrib import admin

from .models import Benefit, Class, Price, Reservation, Room


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
        'adults_capacity',
        'children_capacity',
        'available',
        'image',
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
        status,
    ]


class PriceAdmin(admin.ModelAdmin):
    list_display = ['currency', 'fmt_value', 'active']
    list_filter = ['currency', 'active']

    @admin.display(description='Value')
    def fmt_value(self, obj):
        return f'{obj.value / 100:.2f}'


admin.site.register(Benefit, BenefitAdmin)
admin.site.register(Class, ClassAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Price, PriceAdmin)

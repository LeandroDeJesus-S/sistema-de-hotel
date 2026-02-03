from django.utils.translation import gettext_lazy as _

from .rules import ReserveRules, RoomRules


class Generic:
    UNEXPECTED_ERROR = _('An unexpected error occurred. Please try again later.')
    INVALID_DATA = _('Invalid data.')


class ReservationMessages:
    UNAVAILABLE_ROOM = _('The room is not available for the selected dates.')
    INVALID_DATE_RANGE = _('Check-out date must be after check-in date.')
    SUCCESS = _('Reservation successfully completed.')
    NOT_FOUND = _('Reservation not found.')
    RESERVATION_NOT_FOUND = _('Reservation not found.')
    CANCELED_SUCCESS = _('Reservation successfully cancelled.')
    CANCEL_ERROR = _('Could not cancel the reservation.')
    RESERVATION_FAIL = _('Could not complete the reservation: %(reason)s')
    ALREADY_HAVE_A_RESERVATION = _('You already have an active or scheduled reservation.')
    UNAUTHORIZED_CANCELLATION = _('You do not have permission to cancel this reservation.')
    CANNOT_CANCEL_RESERVATION = _('This reservation cannot be cancelled.')
    CANCELLATION_TOO_LATE = _('Cancellations are only allowed up to 24 hours before check-in.')


class BenefitErrorMessages:
    INVALID_ICON_SIZE = _('The icon must be 64x64.')
    NAME_EMPTY = _('The benefit name cannot be empty.')
    ICON_EMPTY = _('The benefit icon cannot be empty.')
    SHORT_DESC_EMPTY = _('The benefit short description cannot be empty.')
    INVALID_PATTERN = _('The benefit name cannot contain special characters.')


class RoomErrorMessages:
    IMAGE_INVALID_FORMAT = _('Unsupported image type. available: %(available_formats)s') % {
        'available_formats': RoomRules.IMAGE_AVAILABLE_FORMATS
    }
    IMAGE_INVALID_NAME = _('Invalid image name.')
    SHORT_DESC_INVALID = _('Short description provided is invalid')

    ADULTS_INSUFFICIENT = _('Insufficient adults. (min: %(min_adults)s)') % {
        'min_adults': RoomRules.MIN_ADULTS
    }
    CHILD_INSUFFICIENT = _('Insufficient children. (min: %(min_children)s)') % {
        'min_children': RoomRules.MIN_CHILDREN
    }
    SIZE_INSUFFICIENT = _('The room is too small. (min: %(min_size)s)') % {
        'min_size': RoomRules.MIN_SIZE
    }
    PRICE_INSUFFICIENT = _('The room price must be at least $%(min_daily_price).2f.') % {
        'min_daily_price': RoomRules.MIN_DAILY_PRICE
    }

    ADULTS_EXCEEDED = _('Adults capacity exceeded. (max: %(max_adults)s)') % {
        'max_adults': RoomRules.MAX_ADULTS
    }
    CHILD_EXCEEDED = _('Children capacity exceeded. (max: %(max_children)s)') % {
        'max_children': RoomRules.MAX_CHILDREN
    }
    SIZE_EXCEEDED = _('The room is too large. (max: %(max_size)s)') % {
        'max_size': RoomRules.MAX_SIZE
    }
    PRICE_EXCEEDED = _('The room price must be at most $%(max_daily_price).2f.') % {
        'max_daily_price': RoomRules.MAX_DAILY_PRICE
    }
    PRICES_REQUIRED_FOR_AVAILABLE = _('Room must have at least one price to be available.')


class ClasseErrorMessages:
    INVALID_NAME = _('Class name is invalid.')
    NAME_EMPTY = _('Class name cannot be empty.')


class ReserveErrorMessages:
    GENERIC = _('Invalid reservation data')
    INVALID_CHECKIN_DATE = _('Invalid check-in date')
    INVALID_CHECKIN_ANTICIPATION = _(
        'Reservations can only be made up to %(date)s months in advance.'
    ) % {'date': ReserveRules.ANTICIPATED_MONTHS_CHECKIN}
    UNAVAILABLE_ROOM = _('This room is not available.')
    INVALID_STAYED_DAYS = _(
        'The reservation must be from %(min_days)s to %(max_days)s days.'
    ) % {
        'min_days': ReserveRules.MIN_RESERVATION_DAYS,
        'max_days': ReserveRules.MAX_RESERVATION_DAYS,
    }
    INVALID_ROOM_CHOICE = _('Please choose a valid room.')
    UNAVAILABLE_DATE = _('Unavailable reservation date. Available dates are %(dates)s')
    ROOM_NOT_FOUND = _('Could not load room.')
    CLASS_NOT_FOUND = _('Could not load room classes.')

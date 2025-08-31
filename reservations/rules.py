from datetime import datetime, timedelta


class BenefitRules:
    ICON_SIZE = 64, 64


class RoomRules:
    IMAGE_SIZE = 560, 420
    IMAGE_AVAILABLE_FORMATS = ['jpg', 'png']
    MAX_ADULTS = 5
    MIN_ADULTS = 1
    MAX_CHILDREN = 3
    MIN_CHILDREN = 0
    MAX_SIZE = 30
    MIN_SIZE = 2
    MAX_DAILY_PRICE = 500
    MIN_DAILY_PRICE = 100


class ReserveRules:
    MIN_RESERVATION_DAYS = 1
    MAX_RESERVATION_DAYS = 30
    ANTICIPATED_MONTHS_CHECKIN = 3

    @classmethod
    def checkin_anticipation_offset(cls):
        return (datetime.now() + timedelta(weeks=4 * cls.ANTICIPATED_MONTHS_CHECKIN)).date()


class ReserveSupport:
    RESERVATION_PATIENCE_MINUTES = 30  # dependent of stipe :(

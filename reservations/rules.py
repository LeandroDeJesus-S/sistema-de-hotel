from datetime import datetime, timedelta


class BenefitRules:
    ICON_SIZE = 64, 64
    NAME_MAX_LEN = 45
    SHORT_DESC_MAX_LEN = 100
    ICON_MAX_LEN = 255
    NAME_PATTERN = r'^[\w\- ]+$'


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

    NUMBER_FORMAT = r'^\d{3}[A-Z]?$'
    NUMBER_MIN_LEN = 3
    NUMBER_MAX_LEN = 4

    SHORT_DESC_MAX_LEN = 255
    LONG_DESC_MAX_LEN = 1000


class RoomClassRules:
    PATTERN = r'^\w[\w ]*$'
    MIN_LEN = 1
    MAX_LEN = 15


class ReserveRules:
    MIN_RESERVATION_DAYS = 1
    MAX_RESERVATION_DAYS = 30
    ANTICIPATED_MONTHS_CHECKIN = 3

    OBSERVATIONS_MAX_LEN = 100
    OBSERVATIONS_PATTERN = r'[\w\s]*'

    @classmethod
    def checkin_anticipation_offset(cls):
        return (datetime.now() + timedelta(weeks=4 * cls.ANTICIPATED_MONTHS_CHECKIN)).date()


class ReserveSupport:
    RESERVATION_PATIENCE_MINUTES = 30  # dependent of stipe :(

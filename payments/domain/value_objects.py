from enum import Enum


class PaymentStatusEnum(Enum):
    PENDING = 'P'
    FINISHED = 'F'
    CANCELLED = 'C'
    PROCESSING = 'PR'

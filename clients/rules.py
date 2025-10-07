class ClientRules:
    MAX_AGE = 122
    MIN_AGE = 18
    MAX_FIRSTNAME_CHARS = 25
    MIN_FIRSTNAME_CHARS = 2
    MAX_SURNAME_CHARS = 50
    MIN_SURNAME_CHARS = 2

    FIRST_NAME_PATTERN = r'^[^\W\d_]+$'
    LAST_NAME_PATTERN = r'^[^\W\d_ ]+(?: [^\W\d_]+)*$'

    PASSWORD_SUPPORTED_SYMBOLS = "@<>();'-+*;"  # nosec
    PASSWORD_MIN_SIZE = 8
    PASSWORD_MAX_SIZE = 300  # to hashing support

    CPF_MASK_RANGE = 2, -4
    CPF_MIN_SIZE = 11
    CPF_MAX_SIZE = 14

    EMAIL_MASK_RANGE = 2, -2
    PHONE_MASK_RANGE = 4, -4  # ends must be negative
    PHONE_NUMBER_MAX_SIZE = 16
    PHONE_NUMBER_MIN_SIZE = 10

    USERNAME_MAX_SIZE = 150
    USERNAME_MIN_SIZE = 2

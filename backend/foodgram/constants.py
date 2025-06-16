# User model
USERNAME_MAX_LENGTH = 150
EMAIL_MAX_LENGTH = 254
FIRST_NAME_MAX_LENGTH = 150
LAST_NAME_MAX_LENGTH = 150

# Ingredient model
INGREDIENT_NAME_MAX_LENGTH = 128
MEASUREMENT_UNIT_MAX_LENGTH = 64

# Recipe model
RECIPE_NAME_MAX_LENGTH = 256
MIN_COOKING_TIME = 1
MIN_AMOUNT = 1

# Regex patterns
NAME_REGEX = r'^[a-zA-Zа-яА-ЯёЁ\s-]+$'

# Validation messages
NAME_VALIDATION_MSG = 'Name can only contain letters, spaces and hyphens'
MEASUREMENT_UNIT_VALIDATION_MSG = 'Measurement unit can only contain letters, spaces and hyphens' 
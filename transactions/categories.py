"""The ten categories the brief fixes. The value is the label, so the API speaks the same words as the brief."""

from django.db import models


class Category(models.TextChoices):
    GROCERIES = "Groceries"
    DINING_OUT = "Dining Out"
    UTILITIES = "Utilities"
    TRANSPORTATION = "Transportation"
    ENTERTAINMENT = "Entertainment"
    HEALTHCARE = "Healthcare"
    SHOPPING = "Shopping"
    HOUSING = "Housing"
    EDUCATION = "Education"
    MISCELLANEOUS = "Miscellaneous"


CATEGORY_NAMES = [category.value for category in Category]

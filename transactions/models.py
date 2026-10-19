import secrets

from django.db import models

from .categories import Category
from .money import text_from_cents
from .privacy import mask_account


def new_transaction_id():
    return "TXN-" + secrets.token_hex(4).upper()


class TransactionType(models.TextChoices):
    DEBIT = "debit"
    CREDIT = "credit"


class Method(models.TextChoices):
    """How a category was decided (decision 0002)."""

    RULE = "rule"
    CACHE = "cache"
    MODEL = "model"
    FALLBACK = "fallback"


class Transaction(models.Model):
    # The bank's ID when it supplied one, otherwise generated (decision 0003).
    id = models.CharField(primary_key=True, max_length=64, default=new_transaction_id)
    amount_cents = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="EUR")
    timestamp = models.DateTimeField()
    description = models.CharField(max_length=500)
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    account_number = models.CharField(max_length=34)
    created_at = models.DateTimeField(auto_now_add=True)

    # The decision and where it came from.
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.MISCELLANEOUS)
    confidence = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.FALLBACK)
    reason = models.CharField(max_length=200, blank=True, default="")
    model_name = models.CharField(max_length=100, blank=True, default="")
    prompt_version = models.CharField(max_length=20, blank=True, default="")
    categorised_at = models.DateTimeField(null=True, blank=True)
    needs_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp", "id"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["needs_review"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["account_number"]),
        ]

    def __str__(self):
        return f"{self.id} {self.description} {self.amount}"

    @property
    def amount(self):
        return text_from_cents(self.amount_cents)

    @property
    def masked_account(self):
        return mask_account(self.account_number)


class DescriptionCategory(models.Model):
    """The model's decision for one normalised description, per model and prompt version (decision 0002)."""

    normalised_description = models.CharField(max_length=500)
    version = models.CharField(max_length=120)  # "<model name>@<prompt version>"
    category = models.CharField(max_length=20, choices=Category.choices)
    confidence = models.DecimalField(max_digits=3, decimal_places=2)
    reason = models.CharField(max_length=200, blank=True, default="")
    hits = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["normalised_description", "version"], name="one_decision_per_description_and_version")
        ]

    def __str__(self):
        return f"{self.normalised_description!r} -> {self.category} ({self.version})"

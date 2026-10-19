"""The three endpoints from the brief. Validation at the edge, masking on the way out, categorisation on the way in."""

from django.db import transaction as db
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .categories import Category
from .categoriser import categorise
from .models import Method, Transaction, TransactionType
from .money import cents_from_text


class TransactionSerializer(serializers.ModelSerializer):
    """What goes out. The account number is masked; money is a decimal string."""

    amount = serializers.CharField(read_only=True, help_text='Signed decimal string, e.g. "-87.18".')
    account_number = serializers.CharField(source="masked_account", read_only=True, help_text="Masked: first two and last four characters.")
    confidence = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True, coerce_to_string=True)

    class Meta:
        model = Transaction
        fields = ["id", "amount", "currency", "timestamp", "description", "transaction_type", "account_number",
                  "category", "confidence", "method", "reason", "model_name", "prompt_version", "categorised_at",
                  "needs_review", "created_at"]
        read_only_fields = fields


class TransactionInputSerializer(serializers.Serializer):
    """What comes in on POST. A timestamp without a zone is read as Europe/Amsterdam (decision 0003)."""

    id = serializers.RegexField(r"^[A-Za-z0-9_-]{1,64}$", required=False, help_text="The bank's transaction ID. Generated when absent.")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, help_text='Signed decimal, e.g. "-87.18" or -87.18.')
    currency = serializers.RegexField(r"^[A-Z]{3}$", required=False, default="EUR")
    timestamp = serializers.DateTimeField()
    description = serializers.CharField(max_length=500, trim_whitespace=True)
    transaction_type = serializers.ChoiceField(choices=TransactionType.choices)
    account_number = serializers.CharField(max_length=34, trim_whitespace=True)

    def validate_account_number(self, value):
        return value.replace(" ", "").upper()

    def create(self, validated):
        fields = dict(validated)
        fields["amount_cents"] = cents_from_text(fields.pop("amount"))
        with db.atomic():
            record = Transaction(**fields)
            record.save(force_insert=True)
            categorise(record)
        return record


class FilterSerializer(serializers.Serializer):
    """Query parameters for the list. An unknown value is a 400 that names the field, not an empty page."""

    category = serializers.ChoiceField(choices=Category.choices, required=False)
    method = serializers.ChoiceField(choices=Method.choices, required=False)
    needs_review = serializers.BooleanField(required=False)
    account = serializers.CharField(required=False, help_text="The full account number to filter by.")
    since = serializers.DateTimeField(required=False, help_text="Transactions at or after this time.")
    until = serializers.DateTimeField(required=False, help_text="Transactions before this time.")

    def apply(self, queryset):
        f = self.validated_data
        if "category" in f:
            queryset = queryset.filter(category=f["category"])
        if "method" in f:
            queryset = queryset.filter(method=f["method"])
        if "needs_review" in f:
            queryset = queryset.filter(needs_review=f["needs_review"])
        if "account" in f:
            queryset = queryset.filter(account_number=f["account"].replace(" ", "").upper())
        if "since" in f:
            queryset = queryset.filter(timestamp__gte=f["since"])
        if "until" in f:
            queryset = queryset.filter(timestamp__lt=f["until"])
        return queryset


class Pagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500


class TransactionList(generics.ListCreateAPIView):
    """GET: every categorised transaction, newest first, paged. POST: submit one; it comes back categorised."""

    serializer_class = TransactionSerializer
    pagination_class = Pagination

    def get_queryset(self):
        # .dict(): a QueryDict counts as form input, where DRF reads a missing boolean as False instead of absent.
        filters = FilterSerializer(data=self.request.query_params.dict())
        filters.is_valid(raise_exception=True)
        return filters.apply(Transaction.objects.all())

    def create(self, request, *args, **kwargs):
        incoming = TransactionInputSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        wanted_id = incoming.validated_data.get("id")
        if wanted_id and Transaction.objects.filter(pk=wanted_id).exists():
            return Response({"id": [f"transaction {wanted_id} already exists"]}, status=status.HTTP_409_CONFLICT)
        record = incoming.save()
        return Response(TransactionSerializer(record).data, status=status.HTTP_201_CREATED)


class TransactionDetail(generics.RetrieveAPIView):
    """GET one transaction by the ID the bank gave it, or the one we generated."""

    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def get_object(self):
        return get_object_or_404(Transaction, pk=self.kwargs["pk"])

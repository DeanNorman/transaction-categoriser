"""The three endpoints from the brief. Validation at the edge, masking on the way out, categorisation on the way in."""

from django.db import transaction as db
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

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


EXAMPLE_IN = OpenApiExample("A municipal tax payment", value={
    "id": "TXN00001", "amount": "-87.18", "timestamp": "2024-05-16 07:22:18", "description": "Municipal Tax Payment",
    "transaction_type": "debit", "account_number": "NLINGB1944573686"}, request_only=True)
EXAMPLE_OUT = OpenApiExample("Categorised", value={
    "id": "TXN00001", "amount": "-87.18", "currency": "EUR", "timestamp": "2024-05-16T05:22:18Z",
    "description": "Municipal Tax Payment", "transaction_type": "debit", "account_number": "NL******3686",
    "category": "Housing", "confidence": "0.70", "method": "rule",
    "reason": "municipal property and household taxes (decision 0004)", "model_name": "", "prompt_version": "",
    "categorised_at": "2026-10-19T13:00:00Z", "needs_review": False, "created_at": "2026-10-19T13:00:00Z"}, response_only=True)


@extend_schema_view(
    get=extend_schema(
        summary="List categorised transactions",
        description="Newest first, 50 per page (`page_size` up to 500). Every filter value is validated: an unknown category is a 400 that names the field. Account numbers are masked.",
        parameters=[FilterSerializer],
        responses={200: TransactionSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Submit one transaction",
        description="Validated, saved and categorised in one go. The response carries the category, the confidence, how it was decided (rule, cache, model, fallback) and the reason. A timestamp without a zone is read as Europe/Amsterdam. A repeated ID is a 409.",
        request=TransactionInputSerializer,
        responses={201: TransactionSerializer, 400: OpenApiResponse(description="Validation errors, keyed by field"), 409: OpenApiResponse(description="A transaction with this ID already exists")},
        examples=[EXAMPLE_IN, EXAMPLE_OUT],
    ),
)
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


@extend_schema(summary="Fetch one transaction", description="By the ID the bank gave it, or the one generated on submit.", responses={200: TransactionSerializer, 404: OpenApiResponse(description="No such transaction")})
class TransactionDetail(generics.RetrieveAPIView):
    """GET one transaction by the ID the bank gave it, or the one we generated."""

    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def get_object(self):
        return get_object_or_404(Transaction, pk=self.kwargs["pk"])


class ImportSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="A CSV with the columns Transaction ID, Amount, Timestamp, Description, Transaction Type, Account Number.")


IMPORT_REPORT = inline_serializer("ImportReport", {
    "created": serializers.IntegerField(), "skipped": serializers.IntegerField(), "rejected_count": serializers.IntegerField(),
    "rejected": serializers.ListField(child=serializers.DictField(), help_text="The first 50 rejected rows: row number and field errors."),
})


@extend_schema(
    summary="Import a CSV of transactions",
    description="Multipart upload in the brief's column layout. Each row is validated like a submit; existing IDs are skipped, so importing the same file twice is safe; bad rows are reported with their line number. Unknown descriptions cost one model call per distinct description.",
    request=ImportSerializer,
    responses={200: IMPORT_REPORT, 400: OpenApiResponse(description="Missing file, not UTF-8, or the wrong columns")},
)
class TransactionImport(APIView):
    """POST a CSV file; every row is validated, categorised and stored. Existing IDs are skipped, bad rows reported."""

    parser_classes = [MultiPartParser]

    def post(self, request):
        from .importer import BadFile, import_csv  # here, not at the top: importer imports this module

        incoming = ImportSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        try:
            text = incoming.validated_data["file"].read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"file": ["not UTF-8 text"]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            report = import_csv(text)
        except BadFile as error:
            return Response({"file": [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(report.as_dict(), status=status.HTTP_200_OK)


CATEGORY_COUNT = inline_serializer("CategoryCount", {
    "category": serializers.ChoiceField(choices=Category.choices), "count": serializers.IntegerField(),
    "needs_review": serializers.IntegerField(help_text="How many in this category are flagged for a person."),
}, many=True)


@extend_schema(summary="Counts per category", description="All ten categories in the brief's order, with how many transactions landed in each and how many of those need a look. Zero counts are included.", responses={200: CATEGORY_COUNT})
class CategoryCounts(APIView):
    def get(self, request):
        from .review import category_counts  # here, not at the top: review imports this module

        return Response(category_counts(Transaction.objects.all()))

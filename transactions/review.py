"""A page for a person: counts per category, every transaction with its category, how it was decided and why,
and filters. Server-rendered, no frontend build. The same filters as the API, so the two agree."""

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from .api import FilterSerializer
from .categories import Category
from .models import Method, Transaction

PAGE_SIZE = 50


def category_counts(queryset):
    """All ten categories, in the brief's order, with counts (zero included) and how many need a look."""
    by_category = {
        row["category"]: row
        for row in queryset.values("category").annotate(count=Count("id"), needs_review=Count("id", filter=Q(needs_review=True)))
    }
    return [
        {"category": name, "count": by_category.get(name, {}).get("count", 0), "needs_review": by_category.get(name, {}).get("needs_review", 0)}
        for name in Category.values
    ]


def method_counts(queryset):
    by_method = dict(queryset.values_list("method").annotate(n=Count("id")))
    return [{"method": method, "label": label, "count": by_method.get(method, 0)} for method, label in Method.choices]


def review(request):
    filters = FilterSerializer(data=request.GET.dict())
    errors = {} if filters.is_valid() else filters.errors
    everything = Transaction.objects.all()
    rows = filters.apply(everything) if not errors else everything.none()
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "transactions/review.html", {
        "page": page,
        "total": everything.count(),
        "shown": rows.count(),
        "needs_review": everything.filter(needs_review=True).count(),
        "categories": category_counts(everything),
        "methods": method_counts(everything),
        "filters": request.GET,
        "errors": errors,
        "query": query.urlencode(),
        "category_choices": Category.values,
        "method_choices": Method.values,
    })

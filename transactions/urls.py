from django.urls import re_path

from . import api, review

urlpatterns = [
    # The brief writes the paths without a trailing slash; both forms work.
    re_path(r"^transactions/?$", api.TransactionList.as_view(), name="transaction-list"),
    re_path(r"^transactions/import/?$", api.TransactionImport.as_view(), name="transaction-import"),
    re_path(r"^categories/?$", api.CategoryCounts.as_view(), name="category-counts"),
    re_path(r"^review/?$", review.review, name="review"),
    re_path(r"^transactions/(?P<pk>[A-Za-z0-9_-]{1,64})/?$", api.TransactionDetail.as_view(), name="transaction-detail"),
]

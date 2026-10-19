import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_the_schema_renders_and_names_every_endpoint():
    response = APIClient().get("/api/schema")

    assert response.status_code == 200
    schema = response.content.decode()
    for path in ("/transactions", "/transactions/{id}", "/categories"):
        assert f"{path}:" in schema, path
    assert "Groceries" in schema and "Miscellaneous" in schema  # the category enum is in the contract
    assert "securitySchemes" not in schema  # no authentication in this exercise, and the schema says so
    assert "/transactions/import" not in schema  # submissions are one at a time (decision 0006)


@pytest.mark.django_db
def test_the_docs_page_is_served():
    response = APIClient().get("/docs")

    assert response.status_code == 200 and b"swagger" in response.content.lower()

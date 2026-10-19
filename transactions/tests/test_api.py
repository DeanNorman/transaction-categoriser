import pytest
from rest_framework.test import APIClient

from transactions.models import Transaction

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(settings):
    settings.CATEGORISER_PROVIDER = "fake"  # unknown descriptions get the fake's default: Miscellaneous at 0.50
    return APIClient()


def body(**over):
    data = {"id": "TXN00001", "amount": "-87.18", "timestamp": "2024-05-16 07:22:18", "description": "Municipal Tax Payment",
            "transaction_type": "debit", "account_number": "NLINGB1944573686"}
    data.update(over)
    return {k: v for k, v in data.items() if v is not None}


def post(client, **over):
    return client.post("/transactions", body(**over), format="json")


def test_a_submitted_transaction_comes_back_categorised_with_the_reason(client):
    response = post(client)

    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["id"] == "TXN00001" and data["amount"] == "-87.18" and data["currency"] == "EUR"
    assert (data["category"], data["method"], data["confidence"]) == ("Housing", "rule", "0.70")
    assert "municipal" in data["reason"]
    assert data["categorised_at"] is not None


def test_the_account_number_is_masked_in_every_response(client):
    post(client)

    listed = client.get("/transactions").json()["results"][0]
    single = client.get("/transactions/TXN00001").json()
    assert listed["account_number"] == single["account_number"] == "NL******3686"
    assert "NLINGB1944573686" not in str(listed) + str(single)


def test_a_timestamp_without_a_zone_is_read_as_amsterdam_time(client):
    post(client, timestamp="2024-05-16 07:22:18")

    assert Transaction.objects.get().timestamp.isoformat() == "2024-05-16T05:22:18+00:00"


def test_an_id_is_generated_when_none_is_sent(client):
    data = post(client, id=None).json()

    assert data["id"].startswith("TXN-")


def test_validation_errors_name_the_field(client):
    response = client.post("/transactions", {"amount": "abc", "timestamp": "yesterday", "transaction_type": "refund",
                                             "account_number": "NL1"}, format="json")

    assert response.status_code == 400
    assert set(response.json()) >= {"amount", "timestamp", "description", "transaction_type"}


def test_the_same_id_twice_is_a_conflict_not_a_duplicate(client):
    post(client)

    response = post(client)

    assert response.status_code == 409 and Transaction.objects.count() == 1


def test_an_unknown_description_is_categorised_by_the_provider(client):
    data = post(client, description="Fietsenmaker Van Dam").json()

    assert (data["method"], data["model_name"], data["needs_review"]) == ("model", "fake", True)


def test_a_provider_failure_still_saves_the_transaction(client, settings):
    settings.CATEGORISER_PROVIDER = "none"

    response = post(client, description="Fietsenmaker Van Dam")

    assert response.status_code == 201
    data = response.json()
    assert (data["method"], data["category"], data["needs_review"]) == ("fallback", "Miscellaneous", True)
    assert "GEMINI_API_KEY" in data["reason"]


def test_the_list_is_paged_newest_first(client):
    for n, day in ((1, "01"), (2, "02"), (3, "03")):
        post(client, id=f"TXN0000{n}", timestamp=f"2024-05-{day} 12:00:00")

    page = client.get("/transactions?page_size=2").json()

    assert page["count"] == 3 and page["next"] and [t["id"] for t in page["results"]] == ["TXN00003", "TXN00002"]


def test_filters_narrow_the_list_and_bad_filters_are_refused(client):
    post(client, id="A", description="Albert Heijn Purchase", timestamp="2024-05-10 09:00:00")
    post(client, id="B", description="iDEAL Payment", timestamp="2024-05-11 09:00:00")
    post(client, id="C", description="Rent Payment", account_number="NLRABO0000000001", timestamp="2024-06-01 09:00:00")

    def ids(query):
        return [t["id"] for t in client.get(f"/transactions?{query}").json()["results"]]

    assert ids("category=Groceries") == ["A"]
    assert ids("needs_review=true") == ["B"]
    assert ids("method=rule") == ["C", "B", "A"]
    assert ids("account=NLRABO0000000001") == ["C"]
    assert ids("since=2024-05-20T00:00:00Z") == ["C"]
    assert ids("until=2024-05-20T00:00:00Z") == ["B", "A"]
    assert client.get("/transactions?category=Transfers").status_code == 400


def test_an_unknown_id_is_a_404_in_json(client):
    response = client.get("/transactions/TXN99999")

    assert response.status_code == 404 and "detail" in response.json()


def test_both_path_forms_work(client):
    post(client)

    assert client.get("/transactions/").status_code == 200
    assert client.get("/transactions/TXN00001/").status_code == 200

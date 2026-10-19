from config.settings import database_from_url


def test_no_database_url_means_sqlite():
    assert database_from_url(None)["ENGINE"] == "django.db.backends.sqlite3"


def test_postgres_url_is_parsed():
    db = database_from_url("postgres://app:secret@db:5432/transactions")

    assert db["ENGINE"] == "django.db.backends.postgresql"
    assert (db["NAME"], db["USER"], db["PASSWORD"], db["HOST"], db["PORT"]) == ("transactions", "app", "secret", "db", 5432)

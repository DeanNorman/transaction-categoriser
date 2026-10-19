# 0001. Python, Django, Django REST Framework and PostgreSQL

**Status:** accepted, 19 Oct 2026

## Context

The brief asks for the language and framework the author is most comfortable with, with the reasoning written
down. It is a small service: a CSV in, three JSON endpoints out, one model call per unknown description, in Docker.

The author's recent production Python is FastAPI, SQLAlchemy and Pydantic; the team this is for runs Django.

## Decision

Python 3.13, Django 6.1 with Django REST Framework, PostgreSQL 17 through psycopg 3, gunicorn, pytest.

- **Django** gives the parts a data service needs without assembling them: a mature ORM, migrations, transactions,
  settings, a test client, and server-rendered pages for the review screen. For a service whose hard part is the
  data and the rules, not the request handling, that matters more than async.
- **DRF** puts validation at the edge (serializers), gives consistent error shapes, pagination and filtering, and
  with drf-spectacular an OpenAPI schema generated from the code, so the API documentation cannot drift.
- **PostgreSQL** for real constraints (the unique transaction ID that makes imports idempotent) and because it is
  what the service would run on in production. SQLite is used only for fast local tests; nothing Postgres-specific
  is relied on, and CI runs the suite against Postgres too.

## Alternatives

- **FastAPI + SQLAlchemy + Pydantic.** The author's production stack; excellent typed contracts and OpenAPI for free.
  Not chosen because the service is synchronous and CRUD-shaped, and because matching the team's stack is worth
  more here than async. The ideas carried over: typed, validated boundaries, especially around the model's output.
- **Node + TypeScript.** Equally comfortable, but not the backend language of the team.
- **MongoDB.** Offered by the brief. Not chosen: the data is tabular, the queries are filters and counts, and a
  unique constraint is the simplest idempotency there is.

## Consequences

- One framework's conventions throughout; fewer decisions in the code, more in these records.
- Synchronous request handling. Fine for one model call per request and about 20 per thousand-row import (the
  cache in 0002 is why); a queue is the listed next step, not a prerequisite.

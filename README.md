# Transaction categorisation API

[![tests](https://github.com/DeanNorman/transaction-categoriser/actions/workflows/tests.yml/badge.svg)](https://github.com/DeanNorman/transaction-categoriser/actions/workflows/tests.yml)

Submit banking transactions, one at a time or as a CSV, and get them back in one of ten categories with a
confidence, a one-line reason, and a record of how the decision was made: a rule, a cached model answer, the model,
or a fallback flagged for a person. Python, Django and Django REST Framework on PostgreSQL, Gemini for the long
tail of merchants, all in Docker.

Built for a senior engineer assessment. The brief, the decisions and the build plan are in `docs/`; the map of the
work and every pull request are on this repository's issue tracker, starting from
[the map](https://github.com/DeanNorman/transaction-categoriser/issues/1).

## Run it

```sh
cp .env.example .env            # optional: add GEMINI_API_KEY=... for model-backed categorisation
docker compose up --build       # or: make up
```

Then:

| Where | What |
|---|---|
| http://localhost:8000/review | Every transaction with its category, confidence, how it was decided and why; counts per category; filters |
| http://localhost:8000/docs | The API, generated from the code (OpenAPI at `/api/schema`) |
| http://localhost:8000/transactions | The categorised transactions as JSON, paged |
| http://localhost:8000/categories | Counts per category |

On first start the web container migrates the database and imports `data/transaction_history.csv` (the file supplied
with the brief, 1,000 rows), so there is data to look at at once. The import is idempotent: a restart imports
nothing. Without a `GEMINI_API_KEY`, descriptions no rule knows are stored as `Miscellaneous`, method `fallback`,
flagged `needs_review`, with a reason that says what to set. Add the key later and run
`docker compose run --rm web python manage.py recategorise` to upgrade those rows.

Other commands: `make test` (the suite against Postgres, inside the image), `make eval` (score the categoriser
against the gold set), `make decide TEXT="Fietsenmaker Van Dam"` (try one description), `make logs`, `make down`.

## The API

| Method and path | Does |
|---|---|
| `POST /transactions` | Submit one transaction. Validated, saved and categorised; returns the row with its decision. A repeated `id` is a 409. |
| `GET /transactions` | All categorised transactions, newest first, 50 per page (`page_size` up to 500). Filters: `category`, `method`, `needs_review`, `account`, `since`, `until`. An unknown filter value is a 400 that names the field. |
| `GET /transactions/{id}` | One transaction by the bank's ID, or the ID generated on submit. |
| `POST /transactions/import` | A CSV in the brief's column layout, as multipart `file`. Existing IDs are skipped; bad rows are reported with their line number. |
| `GET /categories` | The ten categories with counts, zero included, and how many in each need a look. |

Paths work with or without a trailing slash. There is no authentication in this exercise (see decision 0005).

```sh
curl -s -X POST localhost:8000/transactions -H 'content-type: application/json' -d '{
  "id": "TXN00001", "amount": "-87.18", "timestamp": "2024-05-16 07:22:18",
  "description": "Municipal Tax Payment", "transaction_type": "debit", "account_number": "NLINGB1944573686"}'
```

```json
{
  "id": "TXN00001", "amount": "-87.18", "currency": "EUR", "timestamp": "2024-05-16T07:22:18+02:00",
  "description": "Municipal Tax Payment", "transaction_type": "debit", "account_number": "NL******3686",
  "category": "Housing", "confidence": "0.70", "method": "rule",
  "reason": "municipal property and household taxes (decision 0004)",
  "model_name": "", "prompt_version": "", "categorised_at": "2026-10-19T15:20:20+02:00",
  "needs_review": false, "created_at": "2026-10-19T15:20:20+02:00"
}
```

```sh
curl -s "localhost:8000/transactions?category=Groceries&needs_review=false&page_size=5"
curl -s localhost:8000/transactions/TXN00001
curl -s -F file=@data/transaction_history.csv localhost:8000/transactions/import
```

Reading a response: `amount` is a signed decimal string (money is integer cents inside, never a float); the
account number is masked to its first two and last four characters; `confidence` is the categoriser's own
estimate between 0 and 1; `method` is `rule`, `cache`, `model` or `fallback`; `reason` is the sentence a person
would give; `needs_review` is set when the method is `fallback` or the confidence is under the threshold (0.6).
A timestamp sent without a zone is read as Europe/Amsterdam and shown with its offset.

## How categorisation works

Decision records: [0002](docs/decisions/0002-categorisation-pipeline.md) and [0004](docs/decisions/0004-miscellaneous-and-money-movement.md).

1. **Normalise** the description: lower case, accents and punctuation removed, single spaces. This is the key for
   the rules and the cache.
2. **Rules** (`transactions/rules.py`): an ordered table of known Dutch merchants, housing words, money movement
   and plain words per category. Deterministic, free, instant, and tested row by row against the sample file.
   Transfers, salary, tax, cash withdrawals and card repayments are `Miscellaneous` here on purpose, with the
   reason said, and never reach the model: a confident "Shopping" for a PayPal transfer would be worse than an
   honest Miscellaneous.
3. **Cache**: the model's past answer for this normalised description, keyed by model name and prompt version. The
   sample file costs about 20 model calls, not 1,000, and the same description always gets the same answer.
4. **Model**: Gemini (`google-genai`), with [`prompts/categorise.md`](prompts/categorise.md) as the system
   instruction. The file is the prompt that runs; its version travels with every decision. The model is asked for
   JSON in a fixed schema, at temperature 0, with a 10-second limit, and only ever sees the description. Its answer
   is validated in code (one of the ten categories, confidence in [0, 1]) before anything is stored.
5. **Fallback**: on no key, a timeout, an error or an invalid answer, the transaction is still saved, as
   `Miscellaneous` with confidence 0, method `fallback`, the cause in the reason, and `needs_review` set.

`manage.py decide "<text>"` runs the pipeline on any text and prints the decision.

### Evaluation

`data/gold.csv` holds the twenty sample descriptions and forty-eight edge cases, hand-labelled with a note per
row. `manage.py evaluate` scores the pipeline against it; the numbers are in [`docs/evaluation.md`](docs/evaluation.md).
Rules alone: 58 of 68 right, every rule hit correct, the ten misses all fallbacks, which is the set the model is
for. The model run is added from a real call once a key is set.

## Tests

`make test`, or locally:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest                      # SQLite, fast
DATABASE_URL=postgres://app:app@localhost:5432/transactions .venv/bin/pytest   # against a Postgres
```

137 tests: money and masking; the models; normalisation and every rule against the sample and an unseen merchant
per category; the pipeline's paths (rule, cache, model, four kinds of invalid answer, provider error, threshold);
the Gemini provider with a stubbed client; the API end to end including masking, filters, paging and the error
shapes; the import's idempotency and counts; the schema; the review page; the evaluation and recategorise
commands. CI runs the suite against Postgres and SQLite on every push and pull request.

## Trade-offs and decisions

The full records are in [`docs/decisions/`](docs/decisions/). In short:

- **Rules first, then a model.** Deterministic for the known 80%, a model for the long tail, a cache so the bill is
  predictable. The cost: rules can go stale, so there is an evaluation set and a `recategorise` command.
- **Fail soft.** A model problem never loses a transaction; it produces a flagged row with the cause. The cost: a
  period without a key leaves Miscellaneous rows to upgrade later.
- **The bank's ID is the primary key.** `GET /transactions/TXN00001` means what a reader expects, and re-importing
  a file is safe. The cost: a client that posts without an ID must keep the generated one.
- **Money is integer cents; timestamps without a zone are Amsterdam time.** Exact, and the assumption is written
  down rather than implicit.
- **Money movement is Miscellaneous, with the reason; municipal tax is Housing.** Defensible calls, written down so
  a reviewer can disagree with a sentence.
- **Account numbers are masked; only the description goes to the model; logs carry IDs.** The service's job is
  categories, not identity.
- **Categorisation runs in the request.** One call per unknown description, about 20 for the sample file. A queue
  and batching are the next step at volume, not a prerequisite.
- **No authentication.** Out of scope for the exercise and the first thing before any real deployment.

Listed, not built: authentication and per-client scoping; a queue for large imports; batching descriptions per
model call; a human override endpoint and a decision history table; rate limiting.

## Why Python, Django, DRF and PostgreSQL

Decision record [0001](docs/decisions/0001-stack.md). Django gives a data service its parts without assembly:
ORM, migrations, transactions, a test client, server-rendered pages for the review screen. DRF puts validation at
the edge and, with drf-spectacular, generates the API documentation from the code so it cannot drift. PostgreSQL
for real constraints (the unique ID that makes imports idempotent) and because it is what the service would run on.
The author's recent production Python is FastAPI with SQLAlchemy and Pydantic; Django was chosen here because the
service is synchronous and CRUD-shaped, and because it is the stack of the team this is for. The habits carried
over: typed, validated boundaries, especially around the model's output.

## How it was built

With Claude Code, directed by the author. `CLAUDE.md` is the standing instruction the tool works under in this
repository: decisions before code, one thin slice first, test first in small steps, model output validated in
code, production concerns said out loud, small readable diffs. [`docs/ai-coding-log.md`](docs/ai-coding-log.md)
records how the tool was used and what it got wrong along the way. The work was planned as
[a map on the issue tracker](https://github.com/DeanNorman/transaction-categoriser/issues/1) with one sub-issue per
step, each landed by its own pull request with the test numbers from the run in its body.

## Repository map

| Path | Holds |
|---|---|
| `transactions/` | The app: `models.py`, `rules.py`, `categoriser.py`, `providers/`, `api.py`, `importer.py`, `review.py`, `evaluation.py`, management commands, tests |
| `config/` | Django settings (from the environment), URLs, the schema hook |
| `prompts/categorise.md` | The prompt the model sees, versioned |
| `data/` | The sample CSV from the brief and the gold set |
| `docs/decisions/` | The five decision records; `docs/plan.md`, `docs/evaluation.md`, `docs/ai-coding-log.md` |
| `Dockerfile`, `docker-compose.yml`, `docker/entrypoint.sh`, `Makefile` | Running it |
| `requirements.txt`, `requirements-dev.txt`, `requirements.lock` | Pinned dependencies; the lock is frozen from the built image |

# Build plan

Written before the code, after a short grill of the brief. Steps 1 to 3 landed directly on `main`. From step 4 the
plan lives on the issue tracker as a map with one sub-issue per step, each landed by its own pull request:
[Map: a transaction categorisation service that explains every decision](https://github.com/DeanNorman/transaction-categoriser/issues/1).

1. [x] Repository skeleton: ignore rules, the working agreement (`CLAUDE.md`), the sample data.
2. [x] The thinking: decision records 0001 to 0005, this plan, the AI coding log.
3. [x] Django project: settings from the environment, `transactions` app, pytest wiring, pinned requirements.
4. [x] Data model and migration: `Transaction`, `DescriptionCategory`, the ten categories.
5. [x] Normaliser and rules, with tests for every known merchant and each category.
6. [x] The pipeline: rules, cache, provider seam with a fake, fallback, `needs_review`; tests for each path.
7. [x] Gemini provider: structured output, validation in code, time limit, the prompt as a file; tests with a stub.
8. [x] API: `POST /transactions`, `GET /transactions` (paged, filters), `GET /transactions/:id`; masking; tests.
9. [x] CSV import: `POST /transactions/import` and `manage.py import_csv`; idempotent; counts; tests. The endpoint was
   removed on the day (decision 0006): submissions are one at a time, and a client script feeds a CSV through them.
10. [x] OpenAPI schema and Swagger UI at `/docs`.
11. [x] Review page at `/review`: counts per category, every row with its reason, filters.
12. [x] `GET /categories` with counts.
13. [x] Docker: image, Compose with Postgres, entrypoint that migrates and imports the sample on first run.
14. [x] CI: tests against Postgres on every push.
15. [x] Evaluation: a hand-labelled gold set, `manage.py evaluate`, the numbers in `docs/evaluation.md`.
16. [x] README: setup, API, algorithm and prompts, trade-offs, stack reasoning. Requirements lock from the image.

## Listed, not built

- Authentication and per-client scoping (first thing before any real deployment).
- A queue for imports at volume; batching descriptions per model call.
- A human override endpoint and a categorisation history table.
- Rate limiting; scheduling `recategorise` when rules or the prompt change (the command exists).

17. [x] Single submissions (#27): the bulk endpoint removed, `scripts/post_transactions.py` added, decision 0006.

# Build plan

Written before the code, after a short grill of the brief. Each step is one or two commits; the history should
read like this list. Checked off as they land.

1. Repository skeleton: ignore rules, the working agreement (`CLAUDE.md`), the sample data.
2. The thinking: decision records 0001 to 0005, this plan, the AI coding log.
3. Django project: settings from the environment, `transactions` app, pytest wiring, pinned requirements.
4. Data model and migration: `Transaction`, `DescriptionCategory`, the ten categories.
5. Normaliser and rules, with tests for every known merchant and each category.
6. The pipeline: rules, cache, provider seam with a fake, fallback, `needs_review`; tests for each path.
7. Gemini provider: structured output, validation in code, time limit, the prompt as a file; tests with a stub.
8. API: `POST /transactions`, `GET /transactions` (paged, filters), `GET /transactions/:id`; masking; tests.
9. CSV import: `POST /transactions/import` and `manage.py import_csv`; idempotent; counts; tests.
10. OpenAPI schema and Swagger UI at `/docs`.
11. Review page at `/review`: counts per category, every row with its reason, filters.
12. `GET /categories` with counts.
13. Docker: image, Compose with Postgres, entrypoint that migrates and imports the sample on first run.
14. CI: tests against Postgres on every push.
15. Evaluation: a hand-labelled gold set, `manage.py evaluate`, the numbers in `docs/evaluation.md`.
16. README: setup, API, algorithm and prompts, trade-offs, stack reasoning. Requirements lock from the image.

## Listed, not built

- Authentication and per-client scoping (first thing before any real deployment).
- A queue for imports at volume; batching descriptions per model call.
- A human override endpoint and a categorisation history table.
- Rate limiting; a `recategorise` run when rules or the prompt change (the command exists; scheduling does not).

# The journey of one transaction

What happens to one `POST /transactions`, from the URL to the response, file by file. Line numbers are from the
code at the time of writing; the function names are stable. Each step names the decision record it follows and
the test that pins it, so the walk can be checked, not just read.

The request:

```json
POST /transactions
{"id": "TXN00001", "amount": "-87.18", "timestamp": "2024-05-16 07:22:18",
 "description": "Municipal Tax Payment", "transaction_type": "debit", "account_number": "NLINGB1944573686"}
```

## 1. Routing: `config/urls.py` → `transactions/urls.py:7`

`config/urls.py` includes the app's URLs. `transactions/urls.py:7` matches `^transactions/?$`, so the path works
with or without the trailing slash the brief leaves off, and hands the request to `api.TransactionList`.
Pinned by `tests/test_api.py:123` (`test_both_path_forms_work`).

## 2. Validation at the edge: `transactions/api.py:127` → `:32`

`TransactionList.create` (`api.py:127`) builds `TransactionInputSerializer(data=request.data)` (`api.py:32`):

- `amount` is a `DecimalField` (`:36`): `"-87.18"` or `-87.18`; `"abc"` is a field error, never a silent zero.
- `timestamp` is a `DateTimeField` (`:38`). A value without a zone is read in the project time zone,
  Europe/Amsterdam (`config/settings.py`, `TIME_ZONE`), and stored in UTC. Decision 0003. Pinned by
  `test_api.py:46`.
- `description` must not be blank; `transaction_type` must be `debit` or `credit`; `account_number` is cleaned
  of spaces and upper-cased (`:43`).

Invalid input returns 400 with the errors keyed by field (`test_api.py:58`). If an `id` was sent and already
exists, the view answers 409 before anything is written (`:132`; `test_api.py:66`). Decision 0003: the bank's ID
is the identifier, and a repeat is a conflict, not a duplicate.

## 3. Money and the row: `api.py:46` → `money.py:8` → `models.py:28`

`TransactionInputSerializer.create` (`api.py:46`) turns the amount into integer cents with
`money.cents_from_text` (`api.py:48` → `transactions/money.py:8`): `-87.18` becomes `-8718`, half a cent rounds
up, anything that is not a number is a `ValueError`. Floats never touch money. Pinned by
`tests/test_money_and_privacy.py:8`, `:12`, `:17`.

Inside one database transaction (`api.py:49`), the row is inserted (`:51`) as a `Transaction`
(`transactions/models.py:28`). Its primary key is the ID the bank gave, or `new_transaction_id()`
(`models.py:10`) when none was sent (`test_models.py:28`, `:35`; `test_api.py:52`). The categorisation fields
start as `Miscellaneous` / `fallback` / no time (`test_models.py:51`) until the next step runs.

## 4. The decision: `api.py:52` → `transactions/categoriser.py:71` → `:40`

Still inside the same transaction, `categorise(record)` (`api.py:52` → `categoriser.py:71`) calls `decide`
(`categoriser.py:40`), which runs decision 0002 in order:

1. **Normalise** (`:42` → `transactions/normalise.py:10`): lower case, accents and punctuation gone, single
   spaces. `"Municipal Tax Payment"` → `"municipal tax payment"`. `tests/test_normalise.py`.
2. **Rules** (`:46` → `transactions/rules.py:83`, walking `RULES` from `rules.py:41`): the first pattern that
   matches the normalised text wins. Here `municipal-tax` matches and answers `Housing`, confidence 0.70, reason
   "municipal property and household taxes" (decision 0004). The function returns at once: a rule hit never
   asks the model (`tests/test_categoriser.py:24`). Every one of the twenty sample descriptions is decided
   here (`tests/test_rules.py:34`); so is all money movement, on purpose (`rules.py:68`, `:70`;
   `test_rules.py:72`).
3. **Provider** (`:50` → `transactions/providers/__init__.py:12`): only reached when no rule matched.
   `get_provider()` reads `CATEGORISER_PROVIDER`: `auto` means Gemini when `GEMINI_API_KEY` is set, otherwise
   `NoProvider`, which fails on purpose with a message that says what to set (`test_categoriser.py:142`).
4. **Cache** (`:53` → `models.py:70`): the model's earlier answer for this normalised description and this
   provider version. A hit returns method `cache` and bumps the counter (`:55`); the unique constraint
   (`models.py:83`) keeps one decision per description and version. Second and later sightings of a description
   cost no call (`test_categoriser.py:33`).
5. **Model** (`:59` → `transactions/providers/gemini.py:67`): see the next section.
6. **Fallback** (`:60` → `:36`): any `ProviderError` becomes `Miscellaneous`, confidence 0, method `fallback`,
   the cause in the reason. The transaction is still saved (`test_categoriser.py:69`, `:77`;
   `test_api.py:80`).

## 5. The model, when it is asked: `providers/gemini.py:67`

`GeminiProvider.classify` (`gemini.py:67`):

- The client is built once, with the time limit from `CATEGORISER_TIMEOUT_SECONDS` in milliseconds
  (`gemini.py:48`). Without a key the client is never built and the call fails fast
  (`tests/test_gemini.py:80`).
- The request config (`:52`): the system instruction is the text of `prompts/categorise.md`, loaded by
  `transactions/prompt.py:21`, whose front matter carries the prompt version; the answer must be JSON in
  `ANSWER_SCHEMA` (`gemini.py:12`, `:61`), the ten categories as an enum and a confidence from 0 to 1;
  temperature 0; no thinking budget (`:57`).
- `generate_content` is called with **only the description** as content (`:71`). Not the amount, not the
  account, not the time. Decision 0005. Pinned by `test_gemini.py:42`.
- The text comes back, is parsed as JSON (`:83`) and handed to `validate_answer` (`:86` →
  `transactions/providers/base.py:35`): the category must be one of the ten, the confidence a finite number in
  [0, 1], the reason cut to 200 characters. Anything else is `InvalidAnswer` (`base.py:17`), a kind of
  `ProviderError` (`base.py:13`), so the pipeline falls back rather than storing a bad category
  (`test_gemini.py:55`, `:61`; `test_categoriser.py:61`, `:135`). API errors and timeouts are named the same
  way (`test_gemini.py:66`, `:71`).

A valid answer is written to the cache (`categoriser.py:63`) and returned as method `model`, with the model
name and the prompt version on the decision (`test_categoriser.py:46`).

## 6. Writing the decision: `categoriser.py:71` to `:84`

`categorise` copies the decision onto the row: `category`, `confidence`, `method`, `reason`, `model_name`,
`prompt_version`, `needs_review` and `categorised_at`, then saves (`test_categoriser.py:104`). `needs_review`
(`categoriser.py:32`) is true when the method is `fallback` or the confidence is under `REVIEW_THRESHOLD`
(0.6): here 0.70, so false (`test_categoriser.py:92`). One log line goes out (`:84`) with the transaction ID,
method, category, confidence and the time taken, and never the description or the account
(`test_categoriser.py:124`). Decision 0005.

The database transaction from step 3 commits here. A failure anywhere in steps 3 to 6 rolls back the insert, so
there is never a row without a decision on it.

## 7. The response: `api.py:134` → `:17`

The view returns `TransactionSerializer(record).data` with 201 (`api.py:134`). `TransactionSerializer`
(`api.py:17`) is read-only and shapes the row for the outside:

- `amount` is the signed decimal string from `Transaction.amount` (`models.py:62` →
  `money.text_from_cents`, `money.py:19`): `-8718` → `"-87.18"` (`test_money_and_privacy.py:23`).
- `account_number` is `Transaction.masked_account` (`api.py:21` → `models.py:66` →
  `transactions/privacy.py:4`): `NLINGB1944573686` → `NL******3686`. Every response masks it
  (`test_api.py:37`; `test_money_and_privacy.py:27`).
- `confidence` is a two-decimal string; `timestamp` carries its offset.

```json
{"id": "TXN00001", "amount": "-87.18", "currency": "EUR", "timestamp": "2024-05-16T07:22:18+02:00",
 "description": "Municipal Tax Payment", "transaction_type": "debit", "account_number": "NL******3686",
 "category": "Housing", "confidence": "0.70", "method": "rule",
 "reason": "municipal property and household taxes (decision 0004)", "model_name": "", "prompt_version": "",
 "categorised_at": "2026-10-19T15:20:20+02:00", "needs_review": false, "created_at": "2026-10-19T15:20:20+02:00"}
```

`test_api.py:26` pins the whole journey end to end.

## 8. Afterwards

- `GET /transactions/TXN00001` (`urls.py`, `api.TransactionDetail`) returns the same shape; an unknown ID is a
  JSON 404 (`test_api.py:117`).
- `GET /transactions?category=Housing` lists it; the filters are validated the same way the input was
  (`test_api.py:100`).
- `/review` shows the row with its reason and flag; `/categories` counts it.
- The next transaction with the same description and no rule is a cache hit: one model call per distinct
  description, however many rows (`tests/test_import.py`, "25 rows cost one call").

## The same journey for a description no rule knows

`"Fietsenmaker Van Dam"`: steps 1 to 3 are identical. In step 4 no rule matches, the provider is chosen, the
cache misses, and the model is asked with that one string. With a key: Gemini answers, say, `Transportation` at
0.80, "A fietsenmaker repairs bicycles"; the answer is validated, cached and written, method `model`,
`needs_review` false. Without a key: `NoProvider` raises, the fallback writes `Miscellaneous` at 0, method
`fallback`, reason "model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY ...",
`needs_review` true, and the row is still saved. `manage.py recategorise` upgrades such rows once a key exists.

## Files, in order of appearance

| File | Responsibility in the journey |
|---|---|
| `config/urls.py`, `transactions/urls.py` | Route the request, with or without a trailing slash |
| `transactions/api.py` | Validate the input, refuse a repeated ID, run the write inside one transaction, shape the response |
| `transactions/money.py` | Decimal text ↔ integer cents, exactly |
| `transactions/models.py` | The row, its identifier, the decision fields, the cache table |
| `transactions/categoriser.py` | The order of decision: rules, cache, model, fallback; write and log |
| `transactions/normalise.py` | One form of a description |
| `transactions/rules.py` | The known cases, with confidence and reason |
| `transactions/providers/__init__.py`, `base.py`, `gemini.py`, `none.py`, `fake.py` | The seam to the model, validation of its answer, the real, the absent and the test provider |
| `transactions/prompt.py`, `prompts/categorise.md` | The prompt the model sees, versioned |
| `transactions/privacy.py` | Masking on the way out |

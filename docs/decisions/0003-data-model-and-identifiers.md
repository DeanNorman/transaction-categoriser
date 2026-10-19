# 0003. The bank's transaction ID is the identifier; money is integer cents

**Status:** accepted, 19 Oct 2026

## Context

The CSV carries a `Transaction ID` (TXN00001 ...), a signed decimal amount, a timestamp without a zone, a
description, a debit/credit type and an IBAN. The API has `GET /transactions/:id`. Importing the same file twice
must not create duplicates.

## Decision

- `Transaction.id` is a string primary key: the ID the bank supplied when there is one, otherwise a generated
  `TXN-` plus eight hex characters. `GET /transactions/TXN00001` means what a reader expects, and the primary key
  makes a re-import idempotent: existing IDs are skipped and counted, never duplicated.
- `amount_cents` is a signed integer; `currency` is ISO 4217, default EUR. The API accepts and returns decimal
  strings (`"-87.18"`). Floats never touch money.
- `timestamp` is time-zone aware. A timestamp without a zone is read as Europe/Amsterdam (the data is Dutch) and
  stored in UTC. The assumption is in the importer and in this record, not implicit.
- `transaction_type` is kept as given (`debit` or `credit`) but not used for categorisation: in the sample file it
  disagrees with the sign of the amount at random, so it cannot be trusted. Said in the data notes, not silently
  worked around.
- The categorisation lives on the transaction row (category, confidence, method, reason, model, prompt version,
  categorised at, needs review). One read, one write.
- `DescriptionCategory` holds the model's decision per normalised description and version key (0002).

## Alternatives

- **A surrogate UUID key plus a unique external ID.** Cleaner in theory; two identifiers in practice, and the
  URL would show a UUID nobody recognises.
- **A categorisation history table.** Right once people can override a category and the history matters. Listed
  as the next step; not needed to answer "what category is this, and why".
- **Decimal column for money.** Also exact; integer cents is the convention the author's other services use and
  it keeps arithmetic obvious.

## Consequences

- A client that posts without an ID gets a generated one back and must use it afterwards.
- A re-import reports `created`, `skipped` and `rejected` counts rather than failing.

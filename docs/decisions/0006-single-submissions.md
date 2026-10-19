# 0006. Transactions are submitted one at a time; there is no bulk endpoint

**Status:** accepted, 19 Oct 2026 (replaces the bulk endpoint built under ticket #8)

## Context

The brief asks for "an API for submitting transactions" and supplies the history as a CSV. The first build added a
bulk `POST /transactions/import` next to the single `POST /transactions`. The interviewer's steer on the day: the
way in is single transactions, as a bank integration would send them, not a batch upload.

## Decision

- `POST /transactions` is the only way to submit. One transaction per request, validated, saved and categorised.
- A CSV is fed through that endpoint row by row by a client: `scripts/post_transactions.py`, standard library
  only, which reports created, conflicts (the ID was already there) and rejected rows with the API's field errors.
  The server does all the validating and categorising; the script only posts.
- `manage.py import_csv` stays, for the first-run seed in Docker, so a reviewer sees categorised data at once. It
  goes through the same serializer a POST does, so a seeded row and a posted row are validated identically.
- The bulk endpoint is removed from the code and the schema.

## Alternatives

- Keep both endpoints. Rejected: two ways in means two things to secure, document and keep consistent, and the
  brief asked for one.
- Make the seed post over HTTP too. Rejected: the seed runs before the web server is up; the shared serializer gives
  the same guarantee without the round trip.

## Consequences

- Posting the sample file is 1,000 requests, about a minute against the local stack. That is the integration's
  shape; a queue behind the endpoint is the scaling step, not a batch upload.
- Re-posting a file is safe: existing IDs come back as 409 and are counted, never duplicated.

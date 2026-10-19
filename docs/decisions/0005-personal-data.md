# 0005. IBANs are masked in output, only descriptions reach the model, logs carry IDs

**Status:** accepted, 19 Oct 2026

## Context

An IBAN identifies a person. Descriptions can too ("Salary from Employer", a landlord's name). The service sends
text to a third-party model and writes logs.

## Decision

- Account numbers are stored in full (they are the data) and **masked in every API response**:
  `NLINGB1944573686` becomes `NL**INGB******3686`. A consumer of this API already knows its own accounts; this
  service's job is categories.
- **Only the description goes to the model.** Never the amount, the account, the time or the ID. The prompt has
  no room for them, so this cannot drift by accident.
- Logs carry transaction IDs, methods, outcomes and timings. Never descriptions with amounts, never account
  numbers.
- Secrets come from the environment (`.env`, ignored by git). `DEBUG` is off unless asked for.

## Alternatives

- Return full IBANs because the brief does not mention privacy. Easy to add back behind a flag; hard to take
  back once logged somewhere.
- Send amount and sign to the model to help it (a negative "Rent" is rent paid). Marginal gain, more data out.

## Consequences

- The API is not an authentication layer: it has none. In production a token per client and per-account scoping
  would come before anything else; listed as the first next step.

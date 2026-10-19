# 0004. Money movement is Miscellaneous, with the reason said; municipal tax is Housing

**Status:** accepted, 19 Oct 2026

## Context

Nine of the twenty descriptions in the sample file are not spending at all: transfers between accounts, salary, a
tax refund, an ATM withdrawal, paying off a credit card, and payment rails (iDEAL, PayPal) with no merchant named.
The ten categories are spending categories plus Miscellaneous. Forcing a transfer into "Shopping" would be wrong
in a way that is hard to notice later.

## Decision

- Transfers, income, tax refunds, ATM withdrawals and card repayments are **Miscellaneous by rule**, each with a
  reason that says what it is ("transfer between own accounts", "income", "cash withdrawal, purpose unknown",
  "repayment of a card: the spending was categorised when it happened"). They never reach the model.
- Payment rails with no merchant (`iDEAL Payment`, `PayPal Transfer`) are Miscellaneous with lower confidence
  (0.6) and `needs_review` set: a person with access to the counterparty could do better than any model.
- `Municipal Tax Payment` is **Housing**, confidence 0.7, reason "municipal property and household taxes". Dutch
  municipal taxes (OZB, waste, sewerage) attach to the home. Defensible as Utilities too; the choice is written
  here so a reviewer can disagree with a sentence, not a hunch.
- `Tax Refund` is Miscellaneous (income), not Housing, because it is money in.

## Alternatives

- Add categories such as "Transfers" or "Income". Not allowed: the brief fixes ten.
- Let the model decide these. It would, and plausibly, which is the problem: a confident "Shopping" for a PayPal
  transfer is worse than an honest Miscellaneous.

## Consequences

- About a quarter of the sample file is Miscellaneous. The review page shows why for every row, and the counts
  per category make the proportion visible rather than buried.

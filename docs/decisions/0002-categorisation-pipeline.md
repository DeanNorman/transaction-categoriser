# 0002. Rules first, a model for the rest, every decision checked and explained

**Status:** accepted, 19 Oct 2026

## Context

Transactions must land in one of ten fixed categories. The sample file has 1,000 rows but only 20 distinct
descriptions; real feeds have a long tail of merchants. The brief asks for AI-powered categorisation with the
prompts in the repository. A model call costs money and time, can fail, and can answer outside the allowed set.

## Decision

A pipeline, in this order, with the first step that answers winning:

1. **Normalise** the description: lower case, collapse whitespace, strip punctuation. The key for everything after.
2. **Rules** (`transactions/rules.py`): an ordered list of patterns for known merchants and plain words ("albert
   heijn", "ns ", "rent", "netflix"). Deterministic, free, instant, and tested. A merchant match carries confidence
   0.98, a generic word 0.85. Money movement (transfers, salary, tax, ATM, card repayments) is matched here too, on
   purpose, so it never reaches the model: see 0004.
3. **Cache** (`DescriptionCategory`): the model's past decision for this normalised description, keyed with the
   model name and prompt version. The sample file costs about 20 model calls, not 1,000, and the same description
   always gets the same answer.
4. **Model** (Gemini through `google-genai`, prompt in `prompts/categorise.md`): asked for JSON with `category`,
   `confidence` and a one-line `reason`. The answer is **validated in code**: the category must be one of the ten,
   the confidence a number in [0, 1], the reason short. Anything else is treated as a failure.
5. **Fallback:** on no key, timeout (10 s), error or invalid output, the transaction is still saved, as
   `Miscellaneous` with confidence 0, method `fallback`, the reason naming the cause, and `needs_review` set. A
   model problem never loses a transaction.

Every decision is stored with its provenance: `method` (rule, cache, model, fallback), `confidence`, `reason`,
`model`, `prompt_version`, `categorised_at`. `needs_review` is set when the method is fallback or the confidence is
under a threshold (0.6, a setting). The API and the review page show all of it.

Only the description is sent to the model: not the amount, the account, or the time. See 0005.

## Alternatives

- **Model for everything.** Simplest to explain, and the brief's phrase "AI-powered" could be read that way. Not
  chosen: fifty rows of "Albert Heijn Purchase" don't need a model, and a deterministic first pass is what makes
  the result testable and the bill predictable. The model is still the only thing that handles the unknown.
- **Batching many descriptions in one prompt.** Fewer calls. Not chosen for the first version: one bad answer
  spoils the batch, and per-description answers are easier to validate and cache. Listed as a next step.
- **Fine-tuned or embedding classifier.** Better at scale; far more to build and evaluate. Out of scope.
- **Hard-fail when the model is unavailable.** Honest but loses data. Fail soft with a flag instead.

## Consequences

- Rules can be wrong or go stale. The evaluation set (`data/gold.csv`, `manage.py evaluate`) measures them, and
  `manage.py recategorise` re-runs the pipeline over stored rows when rules or the prompt change, or to upgrade the
  rows that fell back before a model key existed.
- A better prompt or model does not change cached decisions until the version key changes. That is deliberate:
  stability over silent drift.
- Categorisation runs inside the request. A thousand-row import with a cold cache is about 20 calls, roughly 30
  seconds; a queue is the next step at higher volume.

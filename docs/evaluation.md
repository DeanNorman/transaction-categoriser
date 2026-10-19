# Evaluation

How well the categoriser does against `data/gold.csv`: the twenty descriptions from the sample file plus
forty-eight edge cases, four or five per category, hand-labelled, with a note on each row saying why it is there.
The numbers below come from `manage.py evaluate`, pasted, not typed. Accuracy here is exact-match on a small,
author-written set: a reading of where the pipeline is strong and where it is blind, not a benchmark.

Confidence is the categoriser's own estimate (a rule's fixed value, or the model's number). The mean confidence
when right versus when wrong says whether that estimate is worth anything as a review signal.

## Rules alone (no model key) · 19 Oct 2026

**58 of 68 right (85%).**

| Decided by | Right | Of |
|---|---|---|
| fallback | 1 | 11 |
| rule | 57 | 57 |

| Rows | Right | Of |
|---|---|---|
| edge | 38 | 48 |
| sample | 20 | 20 |

| Expected category | Right | Of |
|---|---|---|
| Dining Out | 4 | 5 |
| Education | 3 | 4 |
| Entertainment | 5 | 6 |
| Groceries | 5 | 7 |
| Healthcare | 3 | 5 |
| Housing | 5 | 6 |
| Miscellaneous | 14 | 14 |
| Shopping | 5 | 6 |
| Transportation | 6 | 7 |
| Utilities | 8 | 8 |

Mean confidence when right: 0.90; when wrong: 0.00.

| Description | Expected | Got | By | Confidence | Reason |
|---|---|---|---|---|---|
| Bakkerij Bart Haarlem | Groceries | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Marqt Amsterdam Zuid | Groceries | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Ristorante Il Casale | Dining Out | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Fietsenmaker Van Dam | Transportation | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Rijksmuseum tickets | Entertainment | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Fysiotherapie Zuid | Healthcare | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Huisartsenpraktijk Noord | Healthcare | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Decathlon Utrecht | Shopping | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Interpolis woonverzekering | Housing | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |
| Boekhandel studieboeken | Education | Miscellaneous | fallback | 0.00 | model unavailable: ProviderError: no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake |

### Reading it

- Every rule hit is right: the rules never guess, by design (decision 0002). What they cannot place falls back.
- The ten misses are all fallbacks: a bakery, an organic supermarket, an Italian restaurant name, a bicycle
  repairer, a physiotherapist, a sports shop, a home insurer, a bookshop, and two others no rule knows. That is
  the model's job, and the next section measures it.
- The one fallback that is "right" is `XK-7731 Services BV`, where Miscellaneous is the honest answer.

## Rules plus Gemini

Not yet run: this section is filled in from a real run once a key is available. It will show the same tables
with the fallbacks replaced by model decisions, the model name as it appears in `prompt_version`'s version key,
and the misses the model still makes.

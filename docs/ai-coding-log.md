# How the AI coding tool was used

The brief asks for efficient and thoughtful use of AI coding tools and for the prompts. The categorisation prompt
is in `prompts/`. This file is about the other kind of prompt: how Claude Code was directed to build the
repository. It is kept as the work goes, not reconstructed afterwards.

## Working shape

`CLAUDE.md` at the root is the standing instruction: decisions before code, one thin slice first, test first in
small steps, model output validated in code, production concerns said out loud, small readable diffs. The tool
proposes; the author decides and reads every diff before it is committed.

## The grill (19 Oct 2026)

Before any code, the brief and the data were read and four decisions were put to the author, with a
recommendation each: stack (Django + DRF + Postgres, for fit with the team and a week of recent Django on top of
production FastAPI), model provider (Gemini, which the author can key), repository (public from the first commit,
with the thinking committed too), and extras worth the time (CI, OpenAPI page, review page, accuracy report).

Facts from the data that shaped the design, found by a profiling script before anything was built: 1,000 rows,
no duplicate IDs, 20 distinct descriptions, debit/credit at random against the sign of the amount, nine
descriptions that are money movement rather than spending, three categories that never appear in the data.

## Prompts of note

Recorded as the build goes, one line each: what was asked, what came back, what was changed by hand.

- Decision records 0001 to 0005 and `docs/plan.md`: drafted by the tool from the grill answers, read and corrected
  by the author before the first code commit.
- Data model (#2): the tool proposed masking IBANs as `NL**INGB******3686`; changed by hand to a generic "first two,
  last four" mask that also hides the length, and decision 0005 was corrected to match before the code landed.
- Rules (#4): the tool's first draft of the "unknown merchant" test asserted that an Italian restaurant name *would*
  match a rule; the run failed and the assertion was turned round: an unknown merchant must match nothing, so the
  model gets asked. Caught by running the suite, not by reading.
- Pipeline (#5): nine tests failed at once because the tool had used "Coolblue order 4471" as its example of an
  unknown merchant, and Coolblue is in the shop rule. The rules did their job; the tests were corrected to use a
  merchant no rule knows. A reminder that the fixture has to be checked against the rules, not assumed.
- Gemini provider (#6): the SDK's exact call shape (`HttpOptions.timeout` in milliseconds, `response_json_schema`,
  `ThinkingConfig.thinking_budget`, the `APIError` family) was read from the installed package by introspection
  before any code, instead of trusting memory of the API. The prompt lives in `prompts/categorise.md` and is
  loaded by the code, so the file in the repository is the prompt that runs.
- Process (19 Oct): GitHub closed the stacked rules PR when the data-model branch beneath it was deleted on merge;
  it does not retarget. The PR was reopened against `main`, and the rule from here on is: retarget the dependent PR
  to `main` before merging the PR it stacks on.
- API (#7): one integration test caught that every list query was quietly filtering `needs_review=false`: DRF
  treats a query string as form input, where a missing boolean is False rather than absent. Fixed by passing a
  plain dict. The kind of bug a unit test on the serializer would never have seen.
- CSV import (#8): the importer reuses the POST serializer row by row, so a CSV row is validated exactly like an
  API call and the two can never drift. A test pins that the sample file costs zero provider calls (every
  description has a rule) and that 25 rows of one unknown merchant cost one call.
- Review page (#10): the page reuses the API's filter serializer, so the page and `GET /transactions` agree on what a
  filter means. Patterns borrowed from an earlier project of the author's: status as a mark plus text, confidence
  as a tabular number with a small bar, a left-edge accent on flagged rows, and the line "confidence is the
  categoriser's own estimate, not a measured accuracy". The tool's first draft called an `inline_serializer`
  result as if it were a class; the collection error said so at once.

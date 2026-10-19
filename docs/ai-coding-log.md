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

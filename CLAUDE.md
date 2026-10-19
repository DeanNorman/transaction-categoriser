# Working agreement for this repository

This repository is built with an AI coding tool (Claude Code) directed by a person. These are the rules the tool
follows here, committed so the way the code was made is visible alongside the code.

## Shape of the work

1. **Decisions before code.** The design and its trade-offs live in `docs/decisions/`. A change that alters a
   decision updates its record first.
2. **One thin slice end to end**, then widen. The smallest path from input to a useful output comes first.
3. **Test first, in small steps.** One behaviour per step: a test that fails on its assertion, the smallest code
   that passes it, the whole suite run, one commit with a plain message. Commits are small and logical, so the steps
   can be followed in the history.
4. **AI proposes, code checks, a person decides.** Where a model is involved, its output is structured, validated
   in code against the allowed values, stored with its confidence and reason, and flagged for review when unsure.
   The model never has the last word on data.
5. **Production-ready, said out loud.** Validation at the edge, idempotency for anything that can repeat,
   transactions around multi-step writes, money as integer cents, personal data out of logs and masked in output,
   secrets from the environment, time limits and retries on outside calls, fail soft (a transaction is never lost
   because a model call failed).
6. **Read the diff.** Changes stay small enough to review aloud. If a step touches more than three files, it is
   split.

## Boundaries

- Nothing in this repository is private: no keys, no real account data, no internal notes. `.env` is ignored.
- The prompts the categoriser uses are files under `prompts/`, loaded by the code, so the documented prompt is the
  prompt that runs.
- The sample data under `data/` is the synthetic file supplied with the brief.

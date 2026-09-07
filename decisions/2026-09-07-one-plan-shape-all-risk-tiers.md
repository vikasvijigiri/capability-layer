# One plan shape at every risk tier

## Decision

`task-analysis` emits a single compact plan format — 6-line bullet brief,
four-field task block, 90-line hard cap — regardless of the plan's `**Risk:**`
tier. Risk changes only what an individual task must state inline (a task
touching an irreversible surface names its own rollback and preconditions),
never the length or section set of the plan.

## Why

- The measured cost was in plan **output**, not the skill body: plans ran
  226–555 lines for diffs a fraction of that size. A cap only bites if it is
  unconditional.
- A per-tier split (compact for `low`, full for `medium`/`high`) was built
  first and rejected by the user as still too heavy — a `high`-risk change is
  exactly where a reviewer most needs a plan they will actually read end to
  end, and 300 lines is not that.
- Safety detail that a high-risk plan genuinely needs (per-task rollback,
  preconditions) is preserved by making those fields **required on any task
  that touches an irreversible surface**, rather than by inflating every plan.
- `tools/analyze.py` already had `_rollback_fields_exempt()` — a plan-level
  `## Complexity tracking` line exempting the per-task fields. The compact
  format uses that existing path, so no validator logic changed.

## Alternatives considered

- **Two tiers keyed to `tools/scope.py --plan`** — `low` gets compact,
  `medium`/`high` get today's full template. Built, then dropped: leaves the
  heaviest plans heavy, and adds a branch (`scope.py` tier → template choice)
  to the skill for no reader benefit.
- **Relax `analyze.py` to accept a one-line `**Check:**` per task** instead of
  the `Verification:`/`Run:`/`Expect:`/`Done when:` quartet. Rejected as a
  larger, riskier change touching the validator core and many fixtures, for a
  saving the 90-line cap already delivers.
- **Leave the format, add only a soft "~300 line" guidance line.** That line
  already existed and was routinely ignored; a soft cap with no mechanism is
  not a constraint.

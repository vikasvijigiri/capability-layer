# Plan document format — the exact template

Split out of `task-analysis/SKILL.md`'s Stage C, a compression pass, so the
main body states the procedure once and points here for the literal shape
to copy. Read this at C3/C4, not before.

## One shape, every plan

There is **one** plan format, and it is compact: a 6-line brief, then crisp
one-block tasks. **Hard cap: 90 lines, at any risk tier.** A plan longer than
that is carrying prose a reviewer will not read, or it spans more than one
coherent deliverable (see C1) and should be split — not written longer.

Risk does not change the shape. It changes what each task must *say*: a
high-risk task names its own rollback and preconditions inline (one line
each); a low-risk plan leans on the plan-level `**Rollback:**` and the
standing `## Complexity tracking` exemption. Both pass `tools/analyze.py` and
`tools/parallel_groups.py` unchanged.

## The Progress block (C3)

Every plan carries a `## Progress` block directly above `## Tasks`, one
checkbox per task. `implementation` ticks it as each task's own
**Verification** command runs and is quoted — never on a clean diff alone:

```markdown
## Progress
- [ ] Task 1 — <title>
- [ ] Task 2 [P] — <title>
```

`[P]` after the task number is an optional **reader aid**: this task shares no
file with another in its dependency level, so `parallel_groups.py` will place
it in a concurrent round. It is a hint, not a declaration —
`python tools/parallel_groups.py <plan>` stays the only authority on what may
run together, and it reads `Files:`/`Depends on:`, never this marker. Omit
`[P]` when unsure; a wrong hint costs nothing but a second look.

## The filled instance

One worked plan — the brief is 6 lines, the whole document ~60 with two tasks
and the constitution gate. Copy it whole.

```markdown
# Retry checkout once — Implementation Plan

**Slug:** checkout-retry

- **Goal:** retry a failed checkout once before surfacing the error.
- **Constraints:** `src/checkout.ts` only; no API, schema, or config change.
- **Input:** `src/checkout.ts:submit`, `tests/checkout.test.ts`.
- **Output:** one retry on a 5xx; a second 5xx surfaces to the user.
- **Done Checks:** `npm test -- checkout` exits 0.
- **Out of Scope:** retry counts above one; other call sites.

**Risk:** low — `scope.py --plan` reports no clause forces a tier above low.

**Blast radius:** `src/checkout.ts` only; no consumer, no persisted data.

**Rollback:** revert the commit; the retry holds no state, nothing to unwind.

## Constitution gate
- [x] I Evidence — every task names its command
- [x] II Test first — the failing test precedes the change
- [x] III Smallest change — no refactor beyond the retry
- [x] IV Reversibility — nothing irreversible here
- [x] V No silent degradation — no check is skipped
- [x] VI Mechanism — the one-retry cap is asserted by a test
- [x] VII Secrets — none

## Complexity tracking
Low risk. Per-task Rollback and Preconditions are covered by the plan-level
**Rollback** above and are not repeated per task.

## File map
- `src/checkout.ts` — owns the retry
- `tests/checkout.test.ts` — covers both branches

## Progress
- [ ] Task 1 — retry once on a 5xx
- [ ] Task 2 [P] — cover the retry with a test

## Tasks

### Task 1: retry once on a 5xx
**Files:**
- Modify: `src/checkout.ts:submit` — wrap the call in one retry
**Depends on:** none
**Verification:**
- Run: `npm test -- checkout`
- Expect: 2 passed
**Done when:** one 5xx is retried and a second is surfaced.

### Task 2: cover the retry with a test
**Files:**
- Test: `tests/checkout.test.ts` — retry-then-succeed and retry-then-surface
**Depends on:** none
**Verification:**
- Run: `npm test -- checkout`
- Expect: 2 passed
**Done when:** both branches are asserted and fail without Task 1.
```

## The task block

Four fields, no more — copy this shape:

```markdown
### Task N: [the observable outcome, as the title]
**Files:**
- Create/Modify/Test: `exact/path[:symbol]` — [one line: what it owns / changes]
**Depends on:** [earlier task BY NUMBER, or `none` — never prose, never blank]
**Verification:**
- Run: `[exact command]`
- Expect: [observable passing result]
**Done when:** [a concrete, reviewable condition]
```

- `**Purpose:**` folds into the task title.
- `**Implementation notes:**` is added to a single task **only** where the
  change is not obvious from the files and the outcome — never as a standing
  field.
- `**Rollback:**` / `**Preconditions:**` per task: **required** on any task
  that touches an irreversible surface (a migration, a data write, a
  credential, a release config) — one line each. Otherwise omitted, and the
  `## Complexity tracking` line below is what `tools/analyze.py` reads to
  allow that (`_rollback_fields_exempt`); it must name both words and must be
  present.

`Files:` and `Dependencies:`/`Depends on:` are machine-read — one bullet per
file, full path every time, never a comma-joined list or an inherited prefix
from an earlier bullet (`tools/analyze.py`'s `FILE_RE` and
`tools/parallel_groups.py` both require the exact `- Verb: \`path\`` shape).

## The header

Write the plan at `docs/plans/YYYY-MM-DD-<feature-name>.md`. In order:

1. `# [Feature Name] Implementation Plan`
2. `**Slug:** <unit of work, matching the branch>` — machine-read;
   `tools/resume.py` keys the plan, `refs/uaios/green/<slug>` and the attempt
   ledger off it. A plan named after its feature while the branch is named
   after something else matches nothing.
3. The **6-line brief** as a bullet list: `- **Goal:**`, `- **Constraints:**`,
   `- **Input:**`, `- **Output:**`, `- **Done Checks:**`, `- **Out of Scope:**`
   — one line each, from A2, every inferred field marked `(inferred)`.
4. `**Risk:**` — computed, never judged: run `python tools/scope.py --plan
   <this file>` and paste its one-line reason. Shared or control surface →
   high; volume or spread → medium; a sensitive surface (auth, credentials,
   installer, packaging, CI) → high on its own; unclassifiable → high, never
   low. Not permission to skip Gate 2.
5. `**Blast radius:**` — surfaces, consumers, data this change can reach.
6. `**Rollback:**` — how to undo THIS PLAN at its worst landing state (half
   the tasks merged, already delivered) and what is left behind if the undo
   is not clean.
7. `## Constitution gate`, then `## Complexity tracking`, then `## File map`,
   `## Progress`, `## Tasks`.

`**Risk:**`, `**Blast radius:**` and `**Rollback:**` each sit on their own
line with a blank line around them — a bare run of `**Label:**` paragraphs
collapses into one block. The brief is a bullet list precisely so it does not.

No `## Architecture` or `## Tech stack` section. If the approach needs
explaining, put one sentence in `**Goal:**` or a single task's
`**Implementation notes:**`; if it needs more than that, the approach was not
settled and C1 should have dispatched `architecture`.

## The constitution gate

Every plan carries this block, tick or justify, never silent —
`.claude/constitution.md` holds the articles it names:

```markdown
## Constitution gate
- [ ] I Evidence — every task names the exact command and the expected output
- [ ] II Test first — every behaviour task defines its failing test first
- [ ] III Smallest change — no refactor beyond what the task requires
- [ ] IV Reversibility — irreversible steps are named and gated on a human
- [ ] V No silent degradation — checks that will be skipped are listed here
- [ ] VI Mechanism — any rule this plan adds is enforced by a test or a hook
- [ ] VII Secrets — no credential enters the repo

## Complexity tracking
<one line per unticked box: which article, and why the exception is right>
```

`## Complexity tracking` is always present: it carries the standing line that
exempts the per-task Rollback/Preconditions fields (see the task block above),
plus any unticked-box justification.

Two strings `tools/resume.py` reads as contract, not style:

| Marker | Meaning |
|---|---|
| `[NEEDS CLARIFICATION: q]` | an open question, inline where the answer belongs |
| `## Approved` | the user passed Gate 1 |

**A marker outranks approval.** While any remains, the derived state is
`WAITING_PLAN_APPROVAL` no matter what else the file says.

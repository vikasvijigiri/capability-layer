# Cap the plan self-review loop at 2 iterations — Implementation Plan

**Goal:** Bound `task-analysis`'s existing plan-vs-brief self-review loop
(Stage C5 + `references/artifact-review.md`) at a maximum of 2 review
iterations, so a plan that still fails review after being told what to fix
twice is surfaced at Gate 1 with the residual gap recorded, instead of
looping indefinitely.

**Source brief:** this session's request: "add a skill where it will
iterate on plan against the goal/input the user has asked, with max
iterations = 2." (inferred) Reinterpreted as extending the existing
self-review loop rather than a new skill — see Architecture below.

**Slug:** plan-review-iteration-cap

**Risk:** high — control surface. This edits the skill that governs how
every future plan reaches Gate 1 (`ExitPlanMode`), so a mistake here affects
every subsequent planning session, not just this one. Small in size (2
files, prose + 2 test assertions), but the surface it governs is shared.

**Blast radius:** `task-analysis/SKILL.md` Stage C5 (read by every planning
session), `references/artifact-review.md` (invoked from that stage and
nowhere else), `tools/test_process_router.py` (the suite that already
asserts this skill's cross-file contracts). No runtime hook, no execution
path, no secrets, no packaging/installer/CI surface touched.

**Rollback:** both files are prose/test edits with no state migration —
`git revert` the commit cleanly undoes it. Nothing is written by this
change at plan-authoring time that would need separate cleanup.

**Architecture:** Investigated whether this needed a new skill first
(reuse-before-creating is this repo's explicit rule, and skill-count growth
is a named anti-pattern from the Notion-merge decision record). It doesn't:
`task-analysis` Stage C5 already runs a self-review-and-fix loop against the
plan's own Goal/Input/Output/etc. (via `references/artifact-review.md`'s
APPROVED / APPROVED WITH RECORDED RISK / REVISE verdict), and a REVISE
already sends the author back to fix and re-review. The only real gap is
that this loop is currently **uncapped** — nothing stops a third, fourth,
Nth round. `tools/loop.py`'s rung ladder is a different, already-bounded
mechanism for execution-time failures (code/tests); it does not apply to
plan review, which happens before any code exists.

Per `decisions/2026-08-07-one-workflow-engine.md`'s "one budget table" rule
(attempt counts live in exactly one place, so a second copy can't drift out
of sync and fail by coincidence), the literal number **2** is stated once,
in `task-analysis/SKILL.md` Stage C5 — the stage that owns the loop.
`artifact-review.md` gets one line noting the caller bounds re-dispatch; it
does not restate the count.

**Tech stack and constraints:** Markdown skill-body edits plus
`tools/test_process_router.py` (existing Python test file, already the
place that asserts `task-analysis`'s cross-file prose contracts — reused,
not duplicated). No new file, no new skill directory, no new top-level test
file.

## File map

- Modify: `.claude/skills/task-analysis/SKILL.md` (Stage C5 only) — add the
  2-iteration cap and its Gate-1 fallback.
- Modify: `.claude/skills/task-analysis/references/artifact-review.md`
  (Boundaries section) — one line noting the caller-side cap.
- Modify: `tools/test_process_router.py` — two new `check()` assertions
  reusing the `_wp` variable already loaded at line 509.

## Progress
- [x] Task 1 — Cap Stage C5's self-review loop at 2 iterations
- [x] Task 2 — Assert the cap in `test_process_router.py`, proven to catch its own regression

## Tasks

### Task 1: Cap Stage C5's self-review loop at 2 iterations
**Purpose:** a plan that keeps failing review stops looping and reaches a
human at Gate 1 instead, with the disagreement recorded rather than retried
indefinitely.
**Files:**
- Modify: `.claude/skills/task-analysis/SKILL.md:234-266` (the existing
  "C5. Self-review before handoff" section) — insert the iteration count
  and cap between the `tools/analyze.py` mechanical pass and the six-point
  brief-comparison list that already exists there.
- Modify: `.claude/skills/task-analysis/references/artifact-review.md:33-39`
  (Boundaries) — add: "Called at most twice per plan by `task-analysis`
  Stage C5 before that skill stops iterating and surfaces the residual gap
  at Gate 1 instead — the cap lives there, not here."
**Dependencies:** none
**Implementation notes:** Iteration 1 = the self-review that already exists
today. On REVISE, fix the named gaps, re-run `tools/analyze.py`, re-apply
`artifact-review.md` — that is iteration 2. On a second REVISE, stop: fold
the reviewer's finding into the plan as `[NEEDS CLARIFICATION: <finding,
verbatim>]` at the paragraph it concerns, state "self-review: 2/2,
unresolved — see marker" in the completion summary (Stage "Completion and
handoff"), and proceed to Gate 1 anyway — the marker is what keeps this
honest rather than silently downgrading REVISE to APPROVED. An
APPROVED / APPROVED WITH RECORDED RISK verdict on iteration 1 ends the loop
immediately; iteration 2 only happens after a REVISE. A Stage-B dispatch
(fetching a genuinely missing fact) does not count against the cap — the
cap bounds re-review of an already-drafted plan, not information-gathering.
**Rollback:** revert the two file edits; the loop returns to its current
uncapped behavior.
**Preconditions:** none.
**Verification:**
- Run: `python -c "import pathlib,re; t = pathlib.Path('.claude/skills/task-analysis/SKILL.md').read_text(encoding='utf-8'); assert re.search(r'2.{0,20}iteration', t, re.I), 'cap wording missing'; print('OK')"`
- Expect: prints `OK`, exit 0.
- **Actually run:** printed `OK`.
**Done when:** Stage C5 states the iteration count once, names its Gate-1
fallback, and `artifact-review.md` states the cap is caller-side without
repeating the number.

### Task 2: Assert the cap in `test_process_router.py`, proven to catch its own regression
**Purpose:** the cap is a tested contract, not prose that can drift silently
— matching this repo's own standard (every prose rule here gets a
regression check, per `decisions/2026-08-07-one-workflow-engine.md` and this
session's own hook-staleness fixes).
**Files:**
- Modify: `tools/test_process_router.py` — inserted two `check()` calls
  immediately after the existing `"task-analysis keeps the (inferred)
  marking..."` check (line 540-542), reusing the already-loaded `_wp`
  variable:
  1. `task-analysis` states a 2-iteration self-review cap (regex for
     `2` near `iteration`, same pattern as Task 1's inline check).
  2. `artifact-review.md` does not itself hardcode a competing iteration
     number (load the file, assert no bare digit adjacent to "iteration" —
     keeps the "one place" rule enforced, not just followed once).
**Dependencies:** 1
**Implementation notes:** Matched this file's existing style — a
`check(name, condition, detail)` call, a comment above explaining why the
assertion exists.
**Rollback:** revert the test addition.
**Preconditions:** Task 1 landed (so the first assertion has something true
to check).
**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: both new check names print `OK`, 0 failures reported.
- **Actually run:** `All skill-layer tests passed (14 skills, 8 agents)` —
  both new checks `OK`.
- Then plant the regression: temporarily revert Task 1's Stage C5 wording,
  re-run `python tools/test_process_router.py`, confirm the new check
  prints `FAIL` (not silently passes), then restore Task 1's wording and
  confirm `OK` again.
- **Actually run:** planted (`re.sub` removed `2 ` before `iterations` once),
  re-ran: `FAIL: task-analysis caps its plan self-review loop at 2
  iterations -- an uncapped review-and-fix loop can retry a plan
  indefinitely instead of surfacing the disagreement at Gate 1` — confirmed
  the check catches its own regression. Restored the wording via `Edit`
  (not `git checkout`, which the permission classifier denied as a
  discard-uncommitted-work action); re-ran: green again.
**Done when:** `python tools/test_process_router.py` is green, and the
plant/revert step above is actually run and quoted, not assumed. Met.

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — Task 2's plant-the-regression step proves the test
      fails before it passes, which is the test-first discipline applied to
      a prose contract instead of code
- [x] III Smallest change — no new skill, no new file beyond the two
      modified skill-body files and one existing test file
- [x] IV Reversibility — both tasks are plain edits, `git revert` clean
- [x] V No silent degradation — nothing is skipped; both tasks ran their
      own verification
- [x] VI Mechanism — the rule (cap at 2) is enforced by Task 2's test, not
      left as an unenforced convention
- [x] VII Secrets — none touched

## Complexity tracking
(none — all seven articles ticked)

## Approved

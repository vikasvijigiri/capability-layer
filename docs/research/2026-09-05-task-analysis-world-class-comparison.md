# task-analysis vs. real planning tools — 2026-09-05

**Context:** does `task-analysis` load and produce efficiently, and is its
6-field brief / one-plan-file shape competitive? Compared against source
read directly (not star counts): `github/spec-kit` (★133,520, MIT, pushed
2026-09-04), `eyaltoledano/claude-task-master` (★28,047, pushed 2026-04-28),
`bmad-code-org/BMAD-METHOD` (★52,682, pushed 2026-09-04),
`humanlayer/12-factor-agents` (★25,698, pushed 2025-09-21 — ~1yr stale but
still the canonical citation for "own your context window").

## Measured cost, this repository

| Surface | Size | When paid |
|---|---|---|
| `SKILL.md` body | ~4,471 tokens (17,887 chars) | once per invocation, not per turn |
| `description:` | 599 chars | every turn (in line with the 597-char mean across 15 skills) |
| `references/plan-format.md` + `artifact-review.md` | ~2,100 tokens | at Stage C1/C3/C4 |
| Plans produced this session | 226–555 lines | once, written to `docs/plans/` |
| This session's `docs/constraint-discoverability` plan | 331 lines for a 62-line diff | ~5:1 plan-to-change ratio |

## What real prior art does differently

- **spec-kit's `tasks-template.md`**: one line per task —
  `[ID] [P?] [Story] Description`, e.g. `[ ] T012 [P] [US1] Create Entity1
  model in src/models/entity1.py`. `[P]` is a **visible** marker ("different
  files, no dependencies") a reader sees without running a tool.
- **Task Master's task schema**: `id, title, description, status,
  dependencies, priority, details, testStrategy, subtasks, metadata` — only
  `details`/`testStrategy` are long; the rest is a cheap, scannable,
  machine-queryable row. Subtasks nest under a parent via `expand_task`,
  not written up front for every task.
- **12-factor-agents, Factor 3** ("own your context window"): the concrete
  guidance is a hand-built compact structure beats a verbose default
  format, at equal information content.
- None of the three converges on a shorter *brief* than this skill's six
  fields — spec-kit's `spec.md` is a fuller PRD, Task Master's task record
  carries more fields. The six fields are competitive in scope.

## Verdict

**Strong on rigor, weak on proportionality.** The gate discipline, evidence
requirement, and two-pass self-review exceed what any of the three compared
projects enforce. The token cost is not in `SKILL.md` (a once-per-invocation
cost in line with a skill this consequential) — it is in the **plan output**,
which inlines full task depth unconditionally, for every task, regardless of
size, with no visible parallel marker and no cheap/deep field split.

## Findings, ranked

1. **No visible parallel marker.** `tools/parallel_groups.py` computes
   schedulability after the plan is written; nothing in the task list itself
   shows it, unlike spec-kit's `[P]`. Adding one is additive — the tool stays
   the actual verifier, the marker is a reader aid.
2. **Correction after reading `tools/analyze.py`: a plan-wide exemption
   already exists** (`_rollback_fields_exempt()`) — a plan's own `##
   Complexity tracking` section can name "rollback" and "precondition" to
   exempt every task in that plan from those two fields. This session's
   plans never invoked it, writing `Rollback: git checkout -- <file>` /
   `Preconditions: none` boilerplate on trivial tasks instead — a **usage**
   gap, like the parallel-dispatch one. The residual **design** gap: the
   exemption is all-or-nothing per plan, not per task, so a plan mixing one
   trivial task with one real behavior change can't exempt just the first.
3. **No size-scaled plan shape.** The skill already has a "too small to
   plan" bypass; there is nothing between that and the full Constitution
   gate + Grounding table + Complexity tracking ceremony, which is
   proportionate for an Architecture/Security/Large-feature unit and
   oversized for a Refactor-tier one (this session's three units).
4. **TASK.md should NOT gain the six-field brief.** This is the one place
   the current design already matches the real projects: a cheap, capped,
   injected-every-session index (`TASK.md`, ≤6 rows) pointing at a durable,
   full-detail file read on demand (`docs/plans/*.md`) — the same shape as
   Task Master's task list vs. `details` field, and spec-kit's numbered
   tasks vs. `plan.md`. Merging them would multiply the exact per-session
   cost this session's other unit (constraint discoverability) was about
   reducing.
5. **Parallel-dispatch-at-planning is already correctly separated**, not
   missing. `task-analysis` requires exact `Dependencies:` numbers so
   `parallel_groups.py` can compute rounds; the actual fan-out (worktree per
   task, `backend-engineer`/`frontend-engineer`/`implementer` dispatch,
   batched PR-per-round merge) is `implementation`'s job. The "everything
   happened serially" observation this session is a **usage** gap, not a
   design gap — three small units were each executed inline rather than via
   `parallel_groups.py`, a defensible per-`CLAUDE.md` "cheapest tier" call
   for 1-2 file changes, but real evidence the mechanism goes unused for
   anything smaller than a large feature.

## Not recommended

- Moving the six-field brief into `TASK.md` (finding 4).
- A shorter brief than six fields — no compared project supports one.
- Reducing `SKILL.md`'s per-invocation instruction body — it is not the
  measured cost.

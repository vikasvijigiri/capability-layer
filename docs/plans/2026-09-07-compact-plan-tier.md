# Compact plan format for task-analysis — Implementation Plan

**Slug:** compact-plan-tier

## Approved

Gate 1 passed 2026-09-07 on branch `feat/compact-plan-tier`. Scope narrowed
mid-build by the user: one compact shape for **every** risk tier, ≤90 lines —
not a low-risk-only tier keyed to `scope.py`.

- **Goal:** `task-analysis` emits one plan shape at any risk — a 6-line brief, four-field tasks, 90 lines maximum — replacing the single unbounded template (plans ran 226–555 lines, ~5:1 plan-to-diff).
- **Constraints:** no `tools/analyze.py` logic change; compact plans lint clean and schedule; `- [ ] Task N` progress syntax preserved (`test_process_router.py`); `## Constitution gate` unchanged.
- **Input:** `.claude/skills/task-analysis/references/plan-format.md`, `.claude/skills/task-analysis/SKILL.md` Stage C, `tools/analyze.py` `_rollback_fields_exempt()`, `tools/test_analyze.py`.
- **Output:** one-shape `plan-format.md` (6-line bullet brief, 4-field task block, 90-line cap, `[P]` marker); `SKILL.md` C2–C4 point at it; a `test_analyze.py` fixture proving a compact plan yields zero findings.
- **Done Checks:** `python tools/test_analyze.py` passes · `python tools/run_checks.py --tier all --require-test` exits 0.
- **Out of Scope:** `analyze.py`/`scope.py`/`parallel_groups.py` logic; `TASK.md`; other skills; the `docs/research/` doc (documentation stage records it).

**Risk:** low — `python tools/scope.py --plan` → `risk: low -- no clause forces a tier above low`. `.claude/skills/**` prose is deliberately not a control surface (`tools/scope.py:64`). Not permission to skip Gate 2; `[state:layer-unreviewed]` still requires the layer audit + refactoring sweep before delivery.

**Blast radius:** every future plan `task-analysis` emits; readers of `plan-format.md`; the `analyze.py` exemption path (behaviour unchanged, newly exercised). No runtime code, schema, or other skill.

**Rollback:** revert the squash/merge commit — `plan-format.md` and `SKILL.md` return to the prior single template, the test fixture is removed. No state, flag, or migration.

## Constitution gate
- [x] I Evidence — every task names its command and expected output
- [x] II Test first — Task 3 writes the compact-plan lint fixture; Tasks 1–2 are template/prose verified by `test_analyze.py` + `test_process_router.py`
- [x] III Smallest change — no `analyze.py` logic touched; existing exemption reused
- [x] IV Reversibility — single revert, no state
- [x] V No silent degradation — dropped per-task fields go through the audited `## Complexity tracking` exemption, stated in the compact template
- [x] VI Mechanism — Task 3's fixture is the mechanism that a compact plan stays valid; the format is Stage-C prose like the rest of the skill
- [x] VII Secrets — none

## Complexity tracking
All boxes ticked. Per-task Rollback/Preconditions: this plan's tasks touch
nothing irreversible, so they are covered by the plan-level **Rollback** and
not repeated per task — the `analyze.py:_rollback_fields_exempt` path.

## File map
- Modify: `.claude/skills/task-analysis/references/plan-format.md` — one compact template, 90-line cap, `[P]` in Progress spec
- Modify: `.claude/skills/task-analysis/SKILL.md` — C2–C4 point at the one shape; `[P]` named
- Modify: `tools/test_analyze.py` — `COMPACT` fixture asserting zero findings + ≤90 lines

## Progress
- [ ] Task 1 [P] — one-shape plan-format.md + [P] marker
- [ ] Task 2 — SKILL.md Stage C
- [ ] Task 3 [P] — test_analyze.py compact-plan fixture

## Tasks

### Task 1: one-shape plan-format.md + `[P]` marker
**Files:**
- Modify: `.claude/skills/task-analysis/references/plan-format.md` — single compact template (bullet brief, 4-field task block, 90-line hard cap), `[P]` in the shared Progress spec
**Depends on:** none
**Verification:**
- Run: a script extracting the ```markdown``` filled instance and calling `analyze.analyze(block, exists=lambda _: True, slug="checkout-retry")`
- Expect: findings `[]`; block ≤ 90 lines; `grep -c "^## One shape, every plan" …` → `1`
**Done when:** exactly one plan format is documented, its filled instance lints clean and is ≤ 90 lines, and `[P]` is specified once.

### Task 2: SKILL.md Stage C
**Files:**
- Modify: `.claude/skills/task-analysis/SKILL.md` — C2 states the one ≤90-line shape; C3 names `[P]`; C4 points at the single template
**Depends on:** 1
**Verification:**
- Run: `python tools/test_process_router.py` and `python tools/test_constitution.py`
- Expect: both suites pass (`- [ ] Task N` and the 7 gate lines still resolve across SKILL.md + references)
**Done when:** the skill describes one compact shape and no router/constitution assertion regressed.

### Task 3: test_analyze.py compact-plan fixture
**Files:**
- Modify: `tools/test_analyze.py` — add `COMPACT` fixture + checks that `az.analyze(COMPACT, …) == []` and `len(COMPACT.splitlines()) <= 90`
**Depends on:** none
**Verification:**
- Run: `python tools/test_analyze.py`
- Expect: `All analyze tests passed`; the two new checks reported `OK`
**Done when:** a compact plan (bullet brief, `[P]` progress bullets, Complexity-tracking exemption, no per-task Rollback/Preconditions) is proven to produce zero `analyze.py` findings.

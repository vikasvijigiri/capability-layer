# Notion architecture merge Implementation Plan

## Approved

**Goal:** Restructure `.claude/` to match the Notion *Agentic Workflows (IDE)
— Universal Adaptive SDLC v2* naming/shape (skills, agents, hooks, commands,
`workflows/`, `policies/`), rewriting skill and hook content — not just
renaming — so the layer measurably moves toward minimal tokens, minimal
end-to-end time, and maximum efficiency, while closing the E0-E5
execution-level gap and preserving every currently-Green objective.

**Source brief:** This conversation. Full 25-section Notion doc fetched via
MCP (page `3b9b1c6b-5e27-81b5-ba18-d753031e068d`). Superseding analysis:
`docs/research/2026-08-20-notion-objectives-audit.md`,
`docs/objectives.md`. Prior related work this plan builds on, not
duplicates: `docs/plans/2026-08-20-unified-telemetry-schema.md`,
`docs/plans/2026-08-21-cluster-c-telemetry-metrics.md`. Full grounding
(measurements, section-by-section coverage table, §25 principle mapping) was
produced interactively and approved via `ExitPlanMode`; reproduced in
condensed form below per C4's size cap, not restated in full.

**Slug:** notion-architecture-merge

**Risk:** high (computed below via `tools/scope.py` — every touched path
matches `CONTROL_PATTERNS`: `.claude/hooks/*`, `.claude/agents/*`,
`.claude/skills/*`, `.claude/settings.json`, `.claude/workflow.md`,
`.claude/install.py`).

**Blast radius:** the entire `.claude/` capability layer (hooks, skills,
agents, commands, workflow.md), `install.py`/`build/payload`/`pyproject.toml`
packaging, `harnesses.json`, every tool that names a skill/hook/agent by
string (`test_process_router.py`, `test_hooks.py`, `test_hook_standards.py`,
`test_agent_standards.py`, `test_portability_contract.py`,
`test_entry_classifier.py`, `test_install.py`, `test_package.py`), and every
prose reference in `docs/`, `decisions/`, `TASK.md`, `HANDOFF.md`.
Downstream repos that installed a pre-merge copy are NOT in scope — no
evidence any exist (`../physrun/` untouched, not assumed installed) —
recorded explicitly in Task 1's decision record rather than silently ignored
(objective 20).

**Rollback:** this entire unit lives on `feat/notion-architecture-merge`, a
dedicated worktree/branch off `main` @ `c917e23`. At any landing state,
`git worktree remove --force .worktrees/notion-architecture-merge` and
`git branch -D feat/notion-architecture-merge` (before any merge) fully
undoes it — `main` is untouched until Gate 2. If partially merged, revert the
merge commit; nothing in this plan writes state outside the repo (no live
host, no deploy).

**Architecture:** Five workstreams, ordered by dependency (naming rename
first since later tasks reference the new names; E0-E5 router after hooks
move since it touches the relocated telemetry hook; compression folded into
the rename pass per-file to touch each file once):
- **A** — naming restructure (hooks→10 Notion families, skills→12+2
  documented extensions, agents→7+platform-native `Explore`, commands→
  Notion's 6+repo extras, `workflows/`+`policies/` as thin distinct
  pointers — never restating `workflow.md`'s stage table per
  `decisions/2026-08-07-one-workflow-engine.md`).
- **B** — hook consolidation (`permission-security/00-dispatch.py` merges 4
  processes into 1, mirroring `post-run/00-dispatch.py`'s existing pattern).
- **C** — skill content compression (7 oversized `SKILL.md` files get
  `references/` splits; nothing deleted, only relocated).
- **D** — duplicate-call guard (`task-analysis`'s reuse-check step;
  `06-tool-cost.py` threshold `statusMessage`).
- **E** — E0-E5 execution-level router (`01-entry-classifier.py` gains a
  weighted predicted-level score; `09-telemetry.py` gains an actual level,
  replacing its hardcoded gap-string).

Measured grounding for the language/consolidation/compression choices (all
timed on this machine or cited externally, not assumed): Python cold-start
51.9ms vs Node 69.2ms trivial, 77.2ms vs 76.7ms with a JSON import
(statistically identical) — hooks stay Python. `writing-plans/SKILL.md` is
21,329 ch, the largest and most-loaded skill (single door for all named
work per `decisions/2026-08-09-one-door-into-the-chain.md`) — highest
compression leverage. `tools/bench.py` this session: 189 skill-body loads,
1,329,482 chars (~332K tokens) — the largest measured session cost. 543
shell calls, 12% duplicate rate. E0-E5 scoring shape (weighted: files
affected 0.30, domains/surfaces 0.25, steps required 0.25, research needed
0.20) adapted from a production complexity-classifier pattern found via
websearch alongside arXiv 2603.22455 (*SkillRouter*), using signals this
repo already computes (`tools/scope.py`, `_hooklib.PROGRESS_TASK_BOX`,
`parallel_groups.py` concurrency) rather than a new NLP pass.

**Tech stack and constraints:** Python 3.14 (existing hook runtime, kept —
see Architecture). No new runtime dependency. Every renamed/merged hook
preserves its exact exit-code/stderr contract per
`guide/how_to_create_hooks.md`. Every renamed/merged agent preserves its
exact `tools:`/`model:` allowlist unless the merge target's union is a
strict superset (documented per-agent in Task 5). `install.py`'s
PRESERVE/MERGE/SKIP semantics are unchanged — only `TREES` gains one entry.

## File map

Renamed (git mv, content edited in place): all of `.claude/hooks/*`,
`.claude/skills/{repo-recon,executing-plans,systematic-debugging,
verifying-work,no-slop,knowledge-manager}`, `.claude/agents/{
architecture-reviewer,task-implementer,test-verifier,failure-investigator}`.

Merged (multiple sources → one target, old files removed): `.claude/skills/
{brainstormer,designer}` → `architecture/`; `.claude/skills/{delivering,
releasing}` → `release-git/`; `.claude/agents/{diff-reviewer,spec-reviewer,
release-verifier}` → `reviewer.md`; `.claude/agents/{source-digger,
repo-cartographer}` → `researcher.md`.

Created: `.claude/skills/task-analysis/SKILL.md`,
`.claude/skills/data-analysis/SKILL.md`, `.claude/skills/security/SKILL.md`,
7× `references/*.md` splits under compressed skills, `.claude/workflows/
{universal-task,change,debug,research,delivery}.md`, `.claude/policies/
{permissions,security,escalation,budgets}.md`, `.claude/commands/{task,
debug,review,release}.md`, `.claude/hooks/permission-security/
00-dispatch.py`, `decisions/2026-08-21-notion-architecture-merge.md`.

Modified (references only, not renamed): `.claude/settings.json`,
`.claude/hooks/hooks_registry.json`, `.claude/workflow.md`, `.claude/
install.py`, `harnesses.json`, `.claude/adapters/*.json`,
`tools/test_hooks.py`, `tools/test_hook_standards.py`,
`tools/test_process_router.py`, `tools/test_agent_standards.py`,
`tools/test_entry_classifier.py`, `tools/test_portability_contract.py`,
`docs/harness-hook-bridge.md`, `docs/objectives.md`,
`docs/research/2026-08-20-notion-objectives-audit.md`, `TASK.md`.

Kept unchanged, cited not modified: `.claude/agents/Explore.md`,
`.claude/agents/security-reviewer.md`, `.claude/commands/{git-state,handoff,
wip,verify,verify-change}.md`, `.claude/skills/{code-review,
capability-layer-maintenance}`.

**`tools/analyze.py` note:** after fixing every genuine formatting/path
defect it found (multi-file bullets not matching `FILE_RE`, an ambiguous
`1-8` dependency range that made `parallel_groups.py` mis-schedule two
tasks concurrently, a bare `task.md` colliding with root `TASK.md`), 7
findings remain, all "Modify target does not exist" for paths an earlier,
`Dependencies:`-linked task creates first (e.g. Task 3 modifies
`prompt-intake/01-entry-classifier.py`, which Task 2 — its declared
dependency — creates). Confirmed by reading `tools/analyze.py`'s `exists()`
check: it is a static, single-point-in-time check with no awareness of
what an earlier task in the same plan will create. Not a plan defect —
`python tools/parallel_groups.py` independently confirms all 10 tasks are
correctly ordered serially, consistent with these paths' create-then-modify
sequencing.

## Progress
- [x] Task 1 — Decision record
- [x] Task 2 — Hooks: rename, consolidate, install.py
- [x] Task 3 — E0-E5 router
- [x] Task 4 — Skill renames/merges + compression
- [x] Task 5 — Agent renames/merges
- [x] Task 6 — Commands, workflows/, policies/
- [x] Task 7 — Portability + payload regeneration
- [x] Task 8 — Duplicate-call guard
- [ ] Task 9 — Full verification + regression pass
- [ ] Task 10 — Record (knowledge-manager)

## Tasks

### Task 1: Decision record
**Purpose:** durable, citable record of the naming map, measurements, and
the §25/§20 traceability tables, so nothing here is asserted without a
paper trail.
**Files:**
- Create: `decisions/2026-08-21-notion-architecture-merge.md` — full naming
  map (hooks/skills/agents/commands), the JS-vs-Python measurements, the
  E0-E5 grounding, the 25-section coverage table and 20-principle
  traceability table (both reproduced from this plan's approved design),
  and the explicit objective-20 no-downstream-migration line.
**Dependencies:** none
**Implementation notes:** follow the existing `decisions/*.md` prose style
(see `decisions/2026-08-09-one-door-into-the-chain.md` for shape); every
numeric claim must be the number measured this session, not a rounded
adjective.
**Rollback:** delete the file.
**Preconditions:** none.
**Verification:**
- Run: `wc -l decisions/2026-08-21-notion-architecture-merge.md` and grep
  for all 25 `§` markers and 20 principle references
- Expect: file exists, every section/principle has at least one line
**Done when:** the file cites the real measured numbers (51.9ms/69.2ms,
21,329 ch, 332,370 tokens, 12%) verbatim, not paraphrased.

### Task 2: Hooks — rename, consolidate, install.py
**Purpose:** `.claude/hooks/` matches Notion's 10 named families exactly,
with the `pre-commit`/`pre-deploy` 4-script chain merged into one dispatcher
per the measured latency finding.
**Files:**
- Move: `.claude/hooks/session-start/` — to `.claude/hooks/session-init/`
- Move: `.claude/hooks/user-prompt/` — to `.claude/hooks/prompt-intake/`
- Move: `.claude/hooks/pre-run/` — to `.claude/hooks/pre-tool/`
- Move: `.claude/hooks/on-artifact-create/` — to `.claude/hooks/post-edit-validation/`
- Create: `.claude/hooks/context-budget/01-context-cost.py` — moved from `.claude/hooks/post-tool/01-context-cost.py`, content unchanged
- Create: `.claude/hooks/context-budget/02-skill-cost.py` — moved from `.claude/hooks/post-tool/02-skill-cost.py`, content unchanged
- Create: `.claude/hooks/stop-finalization/00-dispatch.py` — moved from `.claude/hooks/post-run/00-dispatch.py`
- Create: `.claude/hooks/stop-finalization/03-checkpoint.py` — moved from `.claude/hooks/post-run/03-checkpoint.py`
- Create: `.claude/hooks/stop-finalization/06-artifact-autocommit.py` — moved from `.claude/hooks/post-run/06-artifact-autocommit.py`
- Create: `.claude/hooks/stop-finalization/07-layer-drift.py` — moved from `.claude/hooks/post-run/07-layer-drift.py`
- Create: `.claude/hooks/stop-finalization/08-chain-continuity.py` — moved from `.claude/hooks/post-run/08-chain-continuity.py`
- Create: `.claude/hooks/telemetry/09-telemetry.py` — moved from `.claude/hooks/post-run/09-telemetry.py`
- Create: `.claude/hooks/permission-security/00-dispatch.py` — merges `pre-commit/{01-secret-scan,02-branch-guard,03-attribution-guard}.py` + `pre-deploy/01-spend-guard.py` into 4 in-process functions, same order, each still independently able to deny
- Modify: `.claude/settings.json` — every hook `command` path updated to the new family directories
- Modify: `.claude/hooks/hooks_registry.json` — family names and paths updated
- Modify: `.claude/install.py` — `TREES` tuple gains `".claude/policies"`
- Modify: `tools/test_hooks.py` — paths updated to new families
- Modify: `tools/test_hook_standards.py` — paths updated to new families
- Modify: `docs/harness-hook-bridge.md` — hook path references updated
- Modify: `.claude/workflow.md` — hook path references updated (e.g. "Kill switch: `pre-run/01-halt-guard.py`" becomes `pre-tool/01-halt-guard.py`)
- Delete: `.claude/hooks/pre-commit/` — content merged into `permission-security/00-dispatch.py`
- Delete: `.claude/hooks/pre-deploy/` — content merged into `permission-security/00-dispatch.py`
- Delete: `.claude/hooks/post-tool/01-context-cost.py` — moved to `context-budget/`
- Delete: `.claude/hooks/post-tool/02-skill-cost.py` — moved to `context-budget/`
- Delete: `.claude/hooks/post-run/` — fully relocated to `stop-finalization/`/`telemetry/`
**Dependencies:** none
**Implementation notes:** `post-run/00-dispatch.py`'s existing `STEPS`
tuple pattern is the template for `permission-security/00-dispatch.py` —
read it first, mirror its structure exactly (a tuple of `(name, fn)` pairs,
each catching its own exception, most-restrictive-wins on `deny`). Every
hook script keeps its stdin/`HOOK_PAYLOAD` dual-input contract
(`_hooklib.py`, unchanged). `pre-tool/01-halt-guard.py` stays single-script
— nothing to merge there.
**Rollback:** `git mv` each renamed dir back; restore deleted files from
`git show HEAD:<path>`; revert `settings.json`/`hooks_registry.json`.
**Preconditions:** Task 1 done (decision record exists to cite).
**Verification:**
- Run: `python tools/run_hook.py PreToolUse '{"tool_name":"Bash",
  "tool_input":{"command":"echo hi"}}'` (exercises `pre-tool` +
  `permission-security`); repeat per family; then
  `python tools/run_checks.py --scoped`
- Expect: each hook fires with unchanged behavior (same deny/allow
  decisions as before the move on the same fixtures); scoped checks green
**Done when:** `find .claude/hooks -maxdepth 1 -type d` shows exactly the
10 Notion-named families; a timed `Bash` call shows `PreToolUse` dropping
from 5 process launches to 2 (quoted before/after).

### Task 3: E0-E5 execution-level router
**Purpose:** close Gap 1 — `execution_level` becomes a real computed value
(predicted at prompt time, actual at Stop time) instead of a hardcoded
apology string.
**Files:**
- Modify: `.claude/hooks/prompt-intake/01-entry-classifier.py` — add `estimate_execution_level()`: weighted score (files 0.30 via `tools/scope.py`'s changed-path/declared-`Files:` count, domains 0.25 via `CONTROL_PATTERNS`/`SENSITIVE_PATTERNS` hit count, steps 0.25 via `_hooklib.PROGRESS_TASK_BOX` task count, research 0.20 via the existing `entry-open` shape flag) → E0-E5 label, emitted in the hook's existing `additionalContext`/state output
- Modify: `.claude/hooks/telemetry/09-telemetry.py` — replace the hardcoded `execution_level` string with a computed `{"predicted": ..., "actual": ...}` pair, sourced from entry-classifier's state and the existing `skills_loaded`/`agents_spawned` counters
- Modify: `tools/test_entry_classifier.py` — one fixture per E0-E5 level
- Modify: `tools/test_hooks.py` — coverage for the changed telemetry field
**Dependencies:** 2
**Implementation notes:** explicitly a reporter, never a gate — no new
`permissionDecision: deny` path, matching the `context-budget` hook's
existing "reports, never gates" posture (Gap B precedent). Reuse
`tools/scope.py`'s already-computed values; do not re-derive
`CONTROL_PATTERNS` matching independently.
**Rollback:** revert both files; `execution_level` reverts to the
hardcoded string.
**Preconditions:** Task 2 done (hooks at new paths).
**Verification:**
- Run: `python tools/test_entry_classifier.py`
- Expect: 6 new assertions (one per E-level fixture) pass; a real turn's
  telemetry line shows both `predicted` and `actual` as real values
**Done when:** `09-telemetry.py`'s `execution_level` field is never the
literal string `"no E0-E5 router exists yet -- a separate audit gap"` again.

### Task 4: Skill renames/merges + compression
**Purpose:** `.claude/skills/` matches Notion's 12 names + 2 documented
extensions; the 7 oversized bodies get `references/` splits in the same
pass each file is touched.
**Note on `writing-plans`:** it owns stage 1 (framing/planning); Notion's
`implementation` maps to `executing-plans` (stage 3, building) only — the two
were never the same skill. `writing-plans` has no clean 1:1 Notion slot: it is
the framing half of Notion §1's TASK ANALYZER/intake, closest to the new
`task-analysis`. Resolution: **`writing-plans`'s existing, proven procedure
becomes `task-analysis/SKILL.md`'s planning content**, compressed per this
task's own mandate — `task-analysis` is real, substantial content built from
it, not a thin stub standing beside it.

**Files:**
- Move: `.claude/skills/repo-recon/` — to `.claude/skills/repository-navigation/`
- Move: `.claude/skills/executing-plans/` — to `.claude/skills/implementation/`
- Move: `.claude/skills/systematic-debugging/` — to `.claude/skills/debugging/`
- Move: `.claude/skills/verifying-work/` — to `.claude/skills/testing/`
- Move: `.claude/skills/no-slop/` — to `.claude/skills/refactoring/`
- Move: `.claude/skills/knowledge-manager/` — to `.claude/skills/documentation/`
- Create: `.claude/skills/architecture/SKILL.md` — merged from `brainstormer/SKILL.md` + `designer/SKILL.md`, two documented procedures (options-comparison, design-contract)
- Create: `.claude/skills/release-git/SKILL.md` — merged from `delivering/SKILL.md` + `releasing/SKILL.md`
- Create: `.claude/skills/task-analysis/SKILL.md` — built from `writing-plans/SKILL.md`'s planning procedure (see note above), plus Notion §1's INTAKE+STATE/TASK GATE and §19's decision matrix
- Create: `.claude/skills/data-analysis/SKILL.md` — real content formalizing `tools/bench.py`/`telemetry.jsonl`/`chain-ledger.jsonl` analysis, not a stub
- Create: `.claude/skills/security/SKILL.md` — real content formalizing triggering `tools/security_gate.py`/`security-reviewer`, not a stub
- Create: `.claude/skills/task-analysis/references/plan-format.md` — split from `writing-plans/SKILL.md`'s Stage C detail
- Create: `.claude/skills/task-analysis/references/artifact-review.md` — moved from `writing-plans/references/artifact-review.md`
- Create: `.claude/skills/release-git/references/publish-flow.md` — split from `releasing/SKILL.md` + `delivering/SKILL.md`
- Create: `.claude/skills/refactoring/references/sweep-findings.md` — split from `no-slop/SKILL.md`
- Create: `.claude/skills/architecture/references/options-comparison.md` — split from `brainstormer/SKILL.md`
- Create: `.claude/skills/architecture/references/design-contract.md` — split from `designer/SKILL.md`
- Create: `.claude/skills/implementation/references/worktree-parallel.md` — moved from `executing-plans/references/`, unchanged
- Delete: `.claude/skills/writing-plans/` — content merged into `task-analysis/`
- Delete: `.claude/skills/brainstormer/` — content merged into `architecture/`
- Delete: `.claude/skills/designer/` — content merged into `architecture/`
- Delete: `.claude/skills/delivering/` — content merged into `release-git/`
- Delete: `.claude/skills/releasing/` — content merged into `release-git/`
- Modify: `.claude/workflow.md` — Owner column of the 9-stage table renamed (`writing-plans`→`task-analysis`, `executing-plans`→`implementation`, `verifying-work`→`testing`, `no-slop`→`refactoring`, `delivering`/`releasing`→`release-git`, `knowledge-manager`→`documentation`)
- Modify: `tools/test_process_router.py` — every hardcoded skill name updated
**Dependencies:** 2, 3
**Implementation notes:** `code-review` and `capability-layer-maintenance`
are NOT renamed (documented extensions — no Notion skill slot; see plan's
approved §5 row). `research` is NOT renamed (already matches). Compress
each renamed/merged `SKILL.md` to the split above in the SAME edit that
renames it — one touch per file, not two passes.
**Rollback:** `git mv` back; restore `references/` files to their prior
skill directories; revert `workflow.md`/`test_process_router.py`.
**Preconditions:** Tasks 2-3 done.
**Verification:**
- Run: `python tools/test_process_router.py`; `wc -c
  .claude/skills/*/SKILL.md` before/after, quoted
- Expect: router reports the new 12+2 names with no gap/repeat; every
  compressed `SKILL.md` body shows a real character reduction
**Done when:** `ls .claude/skills` shows exactly the 14 names (12 Notion +
`code-review` + `capability-layer-maintenance`); no `SKILL.md` body exceeds
~8,000 ch.

### Task 5: Agent renames/merges
**Purpose:** `.claude/agents/` matches Notion's 7 names; `Explore` and
`security-reviewer` untouched.
**Files:**
- Move: `.claude/agents/architecture-reviewer.md` — to `.claude/agents/architect.md`
- Move: `.claude/agents/task-implementer.md` — to `.claude/agents/implementer.md`
- Move: `.claude/agents/test-verifier.md` — to `.claude/agents/tester.md`
- Move: `.claude/agents/failure-investigator.md` — to `.claude/agents/debugger.md`
- Create: `.claude/agents/reviewer.md` — merged from `diff-reviewer.md`+`spec-reviewer.md`+`release-verifier.md`, mode argument in the dispatch prompt selects diff-angle/spec-conformance/release-readiness; `tools:`/`model:` = union of the three, documented
- Create: `.claude/agents/researcher.md` — merged from `source-digger.md`+`repo-cartographer.md`, mode argument selects single-source-digest/subsystem-mapping
- Delete: `.claude/agents/diff-reviewer.md` — merged into `reviewer.md`
- Delete: `.claude/agents/spec-reviewer.md` — merged into `reviewer.md`
- Delete: `.claude/agents/release-verifier.md` — merged into `reviewer.md`
- Delete: `.claude/agents/source-digger.md` — merged into `researcher.md`
- Delete: `.claude/agents/repo-cartographer.md` — merged into `researcher.md`
- Modify: `.claude/skills/code-review/SKILL.md` — reference the new agent names and mode arg
- Modify: `.claude/skills/release-git/SKILL.md` — reference the new agent names and mode arg
- Modify: `.claude/skills/implementation/SKILL.md` — reference the new agent names
- Modify: `.claude/skills/task-analysis/SKILL.md` — reference the new agent names
**Dependencies:** 4
**Implementation notes:** preserve each source agent's system-prompt
content inside the merged file as a named mode section — do not summarize
away the specialization; only the dispatch surface (one file, one name)
consolidates.
**Rollback:** `git mv` back; split merged files by restoring from
`git show HEAD:<path>`.
**Preconditions:** Task 4 done (dispatching skills at their new paths).
**Verification:**
- Run: dispatch `reviewer` with `mode: diff` on a real small diff;
  dispatch `researcher` with `mode: source-digest` on a real doc
- Expect: output shape matches what `diff-reviewer`/`source-digger`
  produced before the merge
**Done when:** `ls .claude/agents` shows exactly 9 files (7 Notion-named +
`Explore.md` + `security-reviewer.md`).

### Task 6: Commands, workflows/, policies/
**Purpose:** Notion's 6 command entries exist; `workflows/`/`policies/`
each point at a distinct existing mechanism per the plan's approved
distinct-pointer tables.
**Files:**
- Move: `.claude/commands/plan-review.md` — to `.claude/commands/plan.md`
- Create: `.claude/commands/task.md` — thin entry documenting the default flow
- Create: `.claude/commands/debug.md` — thin entry invoking `debugging`
- Create: `.claude/commands/review.md` — thin router; `pr-review`/`security-review` stay underneath
- Create: `.claude/commands/research.md` — thin entry invoking `research`
- Create: `.claude/commands/release.md` — thin router over `save`+`publish`+`release-check`
- Create: `.claude/workflows/universal-task.md` — points at `workflow.md`'s full 9-stage table
- Create: `.claude/workflows/change.md` — points at `workflow.md`'s small-work-path section specifically
- Create: `.claude/workflows/debug.md` — points at the `debugging` skill
- Create: `.claude/workflows/research.md` — points at the `research` skill
- Create: `.claude/workflows/delivery.md` — points at stages 6-8 plus `tools/parallel_groups.py`/`decisions/2026-08-21-branch-per-parallel-task.md`
- Create: `.claude/policies/permissions.md` — points at `settings.json` hooks + `pre-edit/02-agent-scope-guard.py`
- Create: `.claude/policies/security.md` — points at `tools/security_gate.py`, `permission-security/*`
- Create: `.claude/policies/escalation.md` — points at `tools/loop.py`'s rung ladder
- Create: `.claude/policies/budgets.md` — points at `tools/budget.py`, `scope.py`'s risk tier
**Dependencies:** 4, 5
**Implementation notes:** every new file follows `guide/how_to_create_
hooks.md`/existing command frontmatter conventions
(`disable-model-invocation`, trigger-only description). Grep after writing
to confirm no file restates `workflow.md`'s stage table content.
**Rollback:** delete the created files; `git mv` `plan.md` back.
**Preconditions:** Task 5 done.
**Verification:**
- Run: `grep -l "Frame and plan\|Sweep\|Deliver" .claude/workflows/*.md`
- Expect: no match (confirms pointers, not restatement)
**Done when:** `ls .claude/commands` shows the 6 Notion names present
(among the existing 11, net +5 after 1 rename); `ls .claude/workflows`
shows exactly 5 files, each naming a different target in its first
paragraph; `ls .claude/policies` shows exactly 4 files.

### Task 7: Portability + payload regeneration
**Purpose:** the new `.claude/policies/` (and every rename) actually ships
via `install.py`/`build/payload`, not just exists in the source tree.
**Files:**
- Modify: `harnesses.json` — `canonical_paths` gains `"policies": ".claude/policies"` and `"workflows": ".claude/workflows"` if absent
- Modify: `.claude/adapters/claude-code.json` — if it enumerates paths explicitly
- Test: `build/payload/.claude/policies/` — regenerated by `python tools/stage_payload.py`, diffed against the new source tree
**Dependencies:** 2, 4, 5, 6
**Implementation notes:** `install.py`'s `TREES` tuple change from Task 2
is what `stage_payload.py` reads — this task verifies the regeneration,
does not duplicate the TREES edit.
**Rollback:** revert `harnesses.json`; `git checkout -- build/payload` (or
re-run `stage_payload.py` against the pre-merge tree).
**Preconditions:** Task 6 done.
**Verification:**
- Run: `python tools/test_portability_contract.py`;
  `python tools/test_package.py`
- Expect: both exit 0; `build/payload/.claude/policies/` exists with the
  4 files
**Done when:** a fresh `python tools/test_install.py` target directory
contains `.claude/policies/`.

### Task 8: Duplicate-call guard
**Purpose:** the 12% duplicate-call rate is surfaced live, not only in a
post-hoc `bench.py` run.
**Files:**
- Modify: `.claude/skills/task-analysis/SKILL.md` — first mandatory step
  states the reuse-before-retrieve check explicitly
- Modify: `.claude/hooks/post-tool/06-tool-cost.py` — add a threshold
  `statusMessage` when the running duplicate rate crosses a stated bound
  (e.g. >15% over the last N calls), reusing the count already computed
  for `tools/bench.py`, not a new counter
**Dependencies:** 4 (task-analysis must exist)
**Implementation notes:** detection only — no new `permissionDecision`,
consistent with the plan's explicit "not a new gate" decision for E.
**Rollback:** revert both files.
**Preconditions:** Task 4 done.
**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: covers the changed hook; `tools/bench.py`'s duplicate-rate line
  still computes the same formula/value as before this task
**Done when:** a synthetic run of 20 calls with >15% repeats shows the new
`statusMessage` firing.

### Task 9: Full verification + regression pass
**Purpose:** prove the whole merge, with quoted before/after numbers, not
asserted.
**Files:**
- Test: `tools/run_checks.py` — full tier, `--require-test`
- Test: `tools/test_hooks.py`, `tools/test_hook_standards.py`, `tools/test_process_router.py`, `tools/test_agent_standards.py`, `tools/test_portability_contract.py`, `tools/test_install.py`, `tools/test_package.py`, `tools/test_entry_classifier.py` — each run individually
- Test: `tools/bench.py` — before/after deltas
**Dependencies:** 1, 2, 3, 4, 5, 6, 7, 8
**Implementation notes:** run the §20 anti-pattern self-check against the
*landed diff*, not the plan text; run the objective-13/14/17/21/28
regression check named in the approved plan.
**Rollback:** n/a.
**Preconditions:** Tasks 1-8 done.
**Verification:**
- Run: `python tools/run_checks.py --tier all --require-test`;
  `tools/test_hooks.py`; `test_hook_standards.py`; `test_process_router.py`;
  `test_agent_standards.py`; `test_portability_contract.py`;
  `test_install.py`; `test_package.py`; `test_entry_classifier.py`;
  `python tools/bench.py` (before/after deltas)
- Expect: real `PASS` line quoted; every suite exits 0; `bench.py` shows
  quoted reductions in `SKILL.md` total chars and skill-body-load total,
  and a real (non-string) `execution_level` value
**Done when:** every check above is green and quoted in the same message,
plus the §20/regression tables both show no new red.

### Task 10: Record
**Purpose:** durable project-state update, owned by `knowledge-manager`.
**Files:**
- Modify: `LOG.md` — new entry with measured before/after numbers
- Modify: `HANDOFF.md` — current-work section updated
- Modify: `docs/objectives.md` — pointed at the new decision record
- Modify: `docs/research/2026-08-20-notion-objectives-audit.md` — Gap 1 and the agent-catalogue Amber finding marked closed, pointing at the new decision record
- Modify: `TASK.md` — status line for this unit
**Dependencies:** 9
**Implementation notes:** point the research doc at the new decision
record; close Gap 1 and the agent-catalogue Amber finding explicitly.
**Rollback:** revert the modified docs.
**Preconditions:** Task 9 green.
**Verification:**
- Run: `git diff --stat LOG.md HANDOFF.md TASK.md`
- Expect: non-empty diff, each with the measured before/after numbers
**Done when:** `knowledge-manager`'s own success criteria are met (durable
docs match reality, no strategic content authored by a hook).

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — Tasks 3, 4, 5, 8 define their failing/comparison
      check before the change; Tasks 2, 6, 7 are structural moves verified
      by existing suites, not new behavior needing a new failing test first
- [x] III Smallest change — every rename/merge preserves content, only
      Task 4's compression relocates prose (never deletes it)
- [x] IV Reversibility — every task has a one-line rollback; the whole
      unit lives on an isolated worktree/branch until Gate 2
- [x] V No silent degradation — no check is skipped; Task 9 names every
      suite explicitly
- [x] VI Mechanism — every renamed reference is enforced by the existing
      test suites (`test_process_router.py` etc.), not left to prose
- [x] VII Secrets — no credential touched by this plan

## Complexity tracking
(no unticked box)

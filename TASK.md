# Tasks

## Active

<!-- Task(s) currently in progress. Overwrite in place as they change. -->

### Unified per-run telemetry schema
- **Status:** Plan approved (Gate 1) 2026-08-20. See
  `docs/plans/2026-08-20-unified-telemetry-schema.md`. Consolidates
  `bench.session_calls()`, `01-context-cost.py` and `02-skill-cost.py` into
  one per-turn snapshot, closing Gap C from
  `docs/research/2026-08-20-notion-objectives-audit.md`. Chosen as the
  highest-priority of 4 audit candidates (the other 3: E0-E5 execution-level
  router, agent-catalogue decision record, `01-context-cost.py` test
  coverage — not started). Every target-spec field this harness cannot
  populate is named with its reason (`UNAVAILABLE_FIELDS`), not faked. Next:
  `executing-plans`.

### Make the layer portable: it broke every host's test runner

- **Status:** Fixed and proven in Python and Node targets. Payload 1,586,874 ->
  1,172,851 bytes; a fresh install is green in both.
- Create: `tools/conftest.py`
- Modify: `.claude/install.py`, `.claude/hooks/_projectchecks.py`, `tools/test_install.py`, `tools/test_package.py`, `.claude/project-checks.json`, `.claude/constitution.md`, `tools/README.md`, `.claude/skills/writing-plans/SKILL.md`, `.claude/skills/writing-plans/references/plan-document.md`
- **Goal:** installing the layer must not change what the host's own checks mean
  or break the host's test runner.
- **Done Checks:** a fresh install into a Python product runs the product's
  pytest and resolves only the product's checks; the same for a Node product;
  the six shipped validators pass in a target; `--tier all --require-test` green.
- **Out of Scope:** the 36 internal suites no longer ship at all.

### Rewrite skill frontmatter for triggering

- **Status:** Closed 2026-08-16. All 14 rewritten and now MEASURED live rather
  than assumed. Bodies unrestructured except `code-review`.
- Create: `.claude/hooks/post-tool/02-repeat-detector.py`
- Modify: `.claude/workflow.md`, `.claude/hooks/post-tool/01-context-cost.py`, `.claude/hooks/user-prompt/01-entry-classifier.py`, `tools/bench.py`, `.claude/commands/verify.md`, `.claude/hooks/post-tool/01-context-cost.py`, `tools/bench.py`, `.claude/hooks/user-prompt/01-entry-classifier.py`, `.claude/workflow.md`, `.claude/hooks/_projectchecks.py`, `.claude/hooks/hooks_registry.json`, `tools/test_project_checks.py`, `ISSUES.md`, `tools/test_no_slop.py`, `tools/test_process_router.py`, `tools/new_skill_check.py`, `.claude/settings.json`, `.claude/skills/brainstormer/SKILL.md`, `.claude/skills/capability-layer-maintenance/SKILL.md`, `.claude/skills/code-review/SKILL.md`, `.claude/skills/delivering/SKILL.md`, `.claude/skills/designer/SKILL.md`, `.claude/skills/executing-plans/SKILL.md`, `.claude/skills/knowledge-manager/SKILL.md`, `.claude/skills/no-slop/SKILL.md`, `.claude/skills/releasing/SKILL.md`, `.claude/skills/repo-recon/SKILL.md`, `.claude/skills/research/SKILL.md`, `.claude/skills/systematic-debugging/SKILL.md`, `.claude/skills/verifying-work/SKILL.md`, `.claude/skills/writing-plans/SKILL.md`
- **Goal:** maximise the trigger surface so skills actually fire, after
  `code-review` measured `trigger_rate 0.0` on canonical prompts.
- **Constraints:** the listing budget is 1% of context by default and drops
  descriptions least-used-first when it overflows, so trigger words added to one
  skill silently delete another's — `skillListingBudgetFraction` raised to 0.02
  first. Per-entry cap is 1,536 chars. Every `Do NOT use` clause and every
  successor/agent reference preserved.
- **Input:** `code.claude.com/docs/en/skills` frontmatter reference and
  troubleshooting; `anthropics/skills` `template/`, and the `doc-coauthoring`
  and `pdf` descriptions as the trigger-dense exemplars.
- **Output:** descriptions 6,795 → 11,967 ch; listing 8,301 → 13,473 against a
  20,000 budget; largest entry 1,075 of 1,536.
- **Done Checks:** MET 2026-08-16 by live measurement (~$11): `verifying-work`
  trigger_rate 1.0, `systematic-debugging` 0.5, `code-review` 0.0. Descriptions
  trigger; the per-turn cost is bought function. `code-review`'s 0.0 is the
  model doing the review itself and is reached by handoff -- see ISSUES.md.
- **Out of Scope:** the 11 `.claude/commands/` descriptions; restructuring the
  13 remaining skill bodies.

### S1: make every turn cheap

- **Status:** Closed 2026-08-14. Preamble 25,599 -> 9,056 ch, tier 3.4x. The
  per-turn description cost is deliberately unpaid -- see HANDOFF Next Step 0(a).
- Modify: `.claude/hooks/_projectchecks.py`, `tools/test_project_checks.py`, `tools/test_session_start_contract.py`, `CLAUDE.md`, `.claude/skills/verifying-work/SKILL.md`, `.claude/hooks/session-start/02-bootstrap-docs.py`, `README.md`, `.claude/project-checks.json`, `tools/chain.py`, `tools/test_chain.py`, `.claude/workflow.md`, `.claude/hooks/post-run/08-chain-continuity.py`, `tools/eval_triggers.py`, `tools/new_skill_check.py`
- Create: `.claude/operating.md`, `tools/bench.py`, `tools/test_doc_entries.py`
- **Goal:** cut the per-turn cost of this layer without changing what any gate
  decides. Session 1 of three; the router (E0–E5) and the surface trim are S2/S3
  and are not in scope here.
- **Constraints:** no gate may decide differently after this than before it; a
  speedup that costs determinism is a regression, not an optimisation; `--scoped`
  already exists and wiring it into the auto-commit is a *policy* change, so it
  belongs to S2 and is explicitly not done here.
- **Input:** measured baseline — fast tier 61.4s/45 checks serial, `CLAUDE.md`
  14,829 chars, SessionStart output 6,245 chars, descriptions 12,732 chars/turn;
  the Notion target architecture (Universal Adaptive SDLC v2) §15, §20, §21.
- **Output:** `.claude/hooks/_projectchecks.py` (thread pool, `jobs` config knob,
  `DEFAULT_JOBS=8`); `tools/test_project_checks.py` (ordering, `jobs: 1`
  equivalence, timeout vs `ran_test`); `tools/test_session_start_contract.py`
  (label said six, list has seven); then `CLAUDE.md` → ≤5k and the SessionStart
  trim; then `tools/bench.py` as the acceptance gate for S2/S3.
- **Done Checks:** `python tools/run_checks.py --tier all --require-test` exits 0;
  the fast tier is under 20s; `jobs: 1` produces byte-identical output to the
  parallel run (asserted in `test_project_checks.py`).
- **Out of Scope:** the router ADR; description compression (dangerous before the
  router exists); deleting anything from `tools/` — measured at 24/24 live tools
  and a 1.5:1 test:code ratio, so there is no dead weight to remove.

### Audit all ten objectives, then close what blocked "generic" and "world class"

- **Status:** Done 2026-08-16. `4240e61`, `215c4dd`, `a68d283`.
  `PASS: 52 check(s) green`; state reached `WAITING_DELIVERY` for the first time.
- **Goal:** grade the layer against the ten Notion Primary Objectives and
  `GOAL_CHECKLIST.md` with every grade measured, then fix everything blocking
  the "generic" and "partly/in parts" verdicts.
- **Output:** `templates/CODEOWNERS.seed` and a `SEED_SOURCE` indirection;
  Python lint config seeded only into hosts that have Python;
  `run_checks.py --record-green`; the budget's elapsed limb dropped;
  `_projectchecks._run_bounded()`; plan-level `**Rollback:**`/`**Blast radius:**`
  enforced positionally; memory queried at stage 4; `docs/objectives.md`,
  `.claude/README.md`, `.claude/audit/README.md`.
- **Done Checks:** met. Node host resolves 2 checks (its own), Python host 3,
  both green from a fresh install. Hung check: 30.1s → 3.4s against a 3s
  timeout. Both installer guards and the dormancy note proved red by mutation.
- **Not verified:** Gate 2 has still never fired; no run has gone end to end.
- **Out of Scope, and still out:** objective 2's per-turn listing (needs the
  ~$81 trigger measurement, and the evidence points at *more* specific
  descriptions, not shorter); reconciling the two routers (a decision, not a
  merge); anything needing a running service.

### Implement world-class SessionStart bootstrap scaffolding
- **Status:** In Progress
- **Goal:** Implement a SessionStart bootstrap loader that scaffolds project skeleton files and a minimal, maintainable `docs/` structure without creating unnecessary subfolders or a copied `AGENTS.md`.
- **Constraints:** Keep the hook in `.claude/hooks/session-start/02-bootstrap-docs.py`; do not auto-create `AGENTS.md` or copy `CLAUDE.md` into it; prefer a root `docs/` plus only justified category subfolders; follow the hook creation guidance in `guide/how_to_create_hooks.md` and the file-role guidance in `templates/project_docs.md`.
- **Inputs:** current `02-bootstrap-docs.py`, `.claude/settings.json`, `templates/project_docs.md`, `guide/how_to_create_hooks.md`, the repo’s existing docs layout, and the session-start contract tests.
- **Outputs:** updated bootstrap loader script and a documented scaffolding policy for `docs/` and `decisions/`; placeholder files created only where appropriate; task brief recorded.
- **Done Checks:** `python tools/test_session_start_contract.py` exits 0; the loader creates only the intended placeholders; the task brief remains in `TASK.md` and is ready to implement.
- **Out of scope:** generating full content for the skeleton files, creating actual `.claude/agents/` definitions, or changing hooks outside SessionStart.

## Completed

<!-- Append-only, newest entry at the top. Never delete or rewrite an
entry here -- this is the full task/accountability trail for this repo,
from day one. Move a task here the moment it reaches a terminal Status. -->

### 2026-08-20 — Close the router-disagreement and progress-checkbox audit gaps
- **Goal**: close 2 of the 5 gaps found in the 2026-08-16
  capability-layer-maintenance audit — the entry classifier calling a
  control/sensitive-surface change "too small to frame", and four
  independently-defined `## Progress`-checkbox regexes that had begun to
  disagree.
- **Output**: `docs/plans/2026-08-20-router-progress-consistency.md`, 2/2
  tasks. Task 1: `.claude/hooks/user-prompt/01-entry-classifier.py` now
  defers to `tools/scope.py`'s `CONTROL_PATTERNS`/`SENSITIVE_PATTERNS` before
  returning `entry-small`, with a named, tested limitation (a bare filename
  under a wildcard directory pattern is not resolved — would require a
  filesystem read `classify()` deliberately avoids). Task 2: one shared
  `_hooklib.PROGRESS_TASK_BOX`, replacing four private copies across
  `tools/analyze.py`, `tools/chain.py`, `tools/git_ops.py`, `tools/resume.py`.
- **Done Checks**: met. `PASS: 54 check(s) green` fresh, both locally and by
  an independent `test-verifier` dispatch that additionally red-green-proved
  one regression case per task by reverting each source file to `main`'s
  version. `spec-reviewer` returned no findings against the plan. A `no-slop`
  sweep of the 13 changed files found 2 local findings (a naming-consistency
  slip in `chain.py`, this file's own status line going stale the moment the
  work finished) — both repaired and re-verified.
- **Not verified**: end-to-end delivery (PR, merge) — branch
  `fix/router-progress-consistency`, 2 commits, not yet reviewed by
  `code-review` or delivered.
- **Out of Scope, and still out**: the other 3 of the 5 audit gaps, each with
  its own reason recorded in the plan — the per-turn description cost (needs
  a paid ~$81 measurement decision, not a code change), Gate 2 never firing
  end-to-end (emergent from a real delivery, not separately buildable), and
  the two security-gate clauses never firing organically (not fixable by
  writing code).
- **Found during verification, not fixed here**: `tools/resume.py`'s
  `BRANCH_PREFIX = "feat/"` strips only one branch prefix, while
  `.claude/hooks/_hooklib.py`'s `active_plans()` strips five
  (`feat/`/`fix/`/`docs/`/`chore/`/`refactor/`) — confirmed unrelated to this
  diff, but it means `resume.py` cannot resolve this very plan by slug on its
  own `fix/` branch. Worth its own unit.
- **Status**: Done — implementation and sweep complete; delivery pending.

### 2026-08-19 — Close the remaining GOAL_CHECKLIST gaps
- **Goal**: close every remaining checklist gap that has an honest
  implementation, proving deploy stages against a repo with a real surface.
- **Output**: absorbed into `feat/security-gate` rather than run on its own
  branch — `feat/close-remaining-gaps` no longer exists, and its plan doc
  (`docs/plans/2026-08-11-close-remaining-gaps.md`) landed with PR #12.
- **Status**: Done — merged to `main` as part of PR #12, 2026-08-19.

### 2026-08-12 — Retire `/skills-doctor`; three layer-audit doors become two

- **Goal**: decide whether `/skills-doctor` is retired, narrowed, or kept —
  raised by a `no-slop` sweep on 2026-08-03 and open since.
- **Decision**: retired. Its five commands are *all* already registered in
  `.claude/project-checks.json`, so it was a strict subset of `/verify`:
  `ALREADY IN TIER` for `new_skill_check --all`, `test_process_router`,
  `test_agent_standards`, `test_referenced_paths`, `test_command_standards`.
- **What closed the question**: the 2026-08-03 entry kept it alive on one
  argument — that it alone compared disk against the session's *rendered* skill
  listing, which no file-reading script can see. Its own text had since been
  changed to say the opposite: *"Do not claim to inspect the current session's
  rendered system listing; that is not repository-observable."* The narrowing
  option was therefore already impossible, and nothing unique remained.
- **Output**: `.claude/commands/skills-doctor.md` deleted; removed from
  `CLAUDE.md`'s command list, `test_process_router.NOT_SKILLS`, and
  `test_referenced_paths.BUILTIN_COMMANDS`. The two surviving surfaces —
  `no-slop` (sweeps, reports) and `capability-layer-maintenance` (owns the
  contract, repairs) — now state the division on both sides, with two
  assertions in `test_process_router.py` that fail if either stops naming the
  other. Both proved red by breaking each direction.
- **Done Check**: met, by the first of the two branches the 2026-08-03 entry
  offered. `OK: 11 command contracts validated` (was 12).
- **Out of Scope, and still out**: changing what the suites check.
- **Status**: Done

### 2026-08-12 — Deterministic security gate, and the review surfaces it exposed

- **Goal**: a check that refuses a branch which weakens a security control or
  leaves one unchecked — asserting facts about the artefact, never that a review
  happened.
- **Output**: `tools/security_gate.py` + `tools/test_security_gate.py` (64
  assertions); the `audit`-kind entry and two `test_map` rows; a `security`
  finding in `delivery_check.evaluate`; `code-review`'s security lens made
  computed rather than judged; the `no-slop`/`code-review` boundary stated on
  both sides with a suite behind it; `/plan-review`'s dangling `artifact-review`
  fixed and `test_referenced_paths.py` widened to catch that whole class;
  `decisions/2026-08-12-escape-hatches-inherit-trust.md`.
- **Done Checks**: all met. `python tools/test_security_gate.py` exits 0; a real
  removal from `_hooklib.SECRET_PATTERNS` gives `GATE EXIT=1` naming the entry,
  and restoring it gives 0; `PASS: 51 check(s) green (audit, build, lint, smoke,
  test, typecheck)`; `test_referenced_paths.py` exits 0.
- **Result**: `code-review` round 1 returned `passed: false` on a P0 of my own
  making — the inline waiver applied to every clause, so a committed credential
  plus one comment line exited 0. `WAIVABLE_CLAUSES` now holds two of five.
  Round 2 passed. The gate found three real defects on its own repository before
  any of this: an unmapped CI config, five bare-stem reference rots, and two
  bugs in itself.
- **Not verified**: `secret-in-branch` and `dependency-risk` have never fired on
  an organic branch. The `/git-state` fold was planned, attempted and reverted —
  the two commands' bodies do not overlap, so the audit's "five state reporters"
  finding is still open.
- **Out of Scope, and still out**: a fifteenth skill; any receipt or
  process-compliance gate; DAST and offensive testing; the ten unstarted tasks
  of `docs/plans/2026-08-11-close-remaining-gaps.md`.
- **Status**: Done — local on `feat/security-gate` (`d654ee5..4fece17`), not
  pushed, no PR.

### 2026-08-09 — Add an `uninstall` verb, mirroring `install`

- **Goal**: `capability-layer uninstall [--into DIR] [--dry-run]` removes the
  layer it installed, keyed off the v2 manifest, without destroying local edits.
- **Output**: `uninstall_plan()` + `_contained()` + an `--uninstall` branch in
  `.claude/install.py`; the verb in `capability_layer/cli.py` (`_TARGETS`,
  `_PAYLOAD_ONLY`, `_MODE_FLAG`); ~30 assertions in `tools/test_install.py`; a
  "Taking it back out" section in `README.md`. PR #5.
- **Done Checks**: all four met — untouched file removed, edited file kept *and
  named in the report*, `--dry-run` byte-identical (proved by hashing the tree
  before and after), `.claude/settings.json` still present. Each is
  mutation-tested; the final sweep over eight defects reports `hollow: none`.
- **Result**: `code-review` found a path traversal that three `verifying-work`
  passes had cleared — see `ISSUES.md` 2026-08-09 19:30. Two plan amendments and
  two recovery passes are recorded in
  `docs/plans/2026-08-09-uninstall-verb.md`.
- **Out of Scope, and still out**: un-merging `settings.json` hook-by-hook;
  removing `PRESERVE` files; uninstalling from a repo with no manifest.
- **Not verified**: never run against a real third-party repository — every
  fixture is synthetic. `capability-layer uninstall` as a shell command is
  exercised only through the wheel in `test_package.py`.
- **Status**: Done

### 2026-08-02 — Delete the process-compliance gates

- **Goal**: Cut the three hooks that gate process compliance rather than artefact
  correctness, because they had deadlocked against each other and blocked their
  own maintenance work for five sessions.
- **Output**: `pre-commit/03-review-gate.py`, `pre-commit/05-docs-required.py`,
  `post-run/05-docs-gate.py` and `tools/test_docs_gates.py` deleted;
  `settings.json` and `hooks_registry.json` down to 25 hooks; `test_hooks.py`
  sections 4-5 removed; `code-review`, `delivering`, `executing-plans` and
  `knowledge-manager` rewritten to stop instructing a script that no longer
  exists; `/verify`, `CLAUDE.md`, `.claude/workflow.md`, `tools/README.md`
  corrected from seven suites to six.
- **Status**: Done — supersedes the 2026-08-01 entry below, which was accurate
  when written. The deadlock it could not see: `03-review-gate.py` fingerprinted
  the whole working tree, so writing the log entry `05-docs-required.py` demanded
  invalidated the receipt `03-review-gate.py` demanded. Measured, not inferred.
  Five comparable GitHub repos gate artefacts, none gates process.

### 2026-08-01 — Review gate that always asks before a commit or PR

- **Goal**: A `code-review` skill that reviews the pending diff or PR, reports
  findings, and requires explicit user sign-off — where that sign-off is the only
  thing that writes the receipt `03-review-gate.py` checks, so an unreviewed
  commit or PR is always interrupted.
- **Input**: `03-review-gate.py` (working gate, `--record` mode, content
  fingerprinting); `04-delivery-guard.py` (mechanical checks, already emits an
  unverifiable "was this reviewed" note per commit);
  `.claude/hooks/state/review-receipts.json`, holding one stale receipt;
  `git diff` / `gh pr diff` / the GitHub MCP for PR content.
- **Output**: `.claude/skills/code-review/SKILL.md`; a `## code-review` entry in
  `.claude/workflow.md`; current review-gate coverage extended to match PR
  actions; coverage for the new trigger in `tools/test_hooks.py`.
- **Constraints**: Extend `03-review-gate.py` to match `gh pr create` / PR
  actions — today it matches only `git commit` and `git push`. Write the receipt
  through the existing `--record` mode; the fingerprint scheme and receipts file
  are unchanged. Never self-record: no findings still requires sign-off, or the
  every-time ask is lost. Needs a routing entry (`test_process_router.py`
  enforces it). Follow the superpowers SKILL.md shape — trigger-only description
  under 500 chars, Red Flags, Common Mistakes.
- **Done Checks**:
  1. `echo '{"tool_name":"Bash","tool_input":{"command":"gh pr create"}}' | python .claude/hooks/pre-commit/03-review-gate.py`
     returns `permissionDecision: ask` on a dirty tree. Today it is silent.
  2. After `--record`, the same payload is silent; after any further edit it
     returns `ask` again.
  3. `python tools/test_hooks.py` and `python tools/test_process_router.py` both
     exit 0, the router reporting `4 entries routed`.
- **Out of Scope**: The `\claude\` Windows false-positive in
  `04-delivery-guard.py` (separate pending item). The secret-scan `deny` —
  untouched. Posting review comments back to GitHub. Deleting the stale receipt
  beyond what `--record` overwrites. Reviving any other deleted skill.
- **Result**: All three Done Checks pass. Also fixed a latent bug the brief did
  not anticipate: the receipts file is tracked, so `--record` changed the very
  fingerprint it had just recorded under, and every receipt self-invalidated.
  The gate had never been able to pass. Receipts path is now excluded from all
  fingerprint inputs.
- **Status**: Done

### 2026-07-30 — Wire repo hooks into Claude Code lifecycle events
- **Goal**: Make `.claude/hooks/` fire automatically instead of only when something
  shells out to `tools/run_hook.py`.
- **Output**: `.claude/settings.json` registering 9 of 10 repo events directly;
  `.claude/hooks/_hooklib.py`; all 11 hook scripts rewritten to accept both stdin and
  `HOOK_PAYLOAD`; two new hooks (`pre-commit/02-branch-guard.py`,
  `post-run/03-checkpoint.py`); `.claude/commands/save.md`. Verified live plus three
  suites (11/11 repo, 17/17 stdin, 17/17 git).
- **Status**: Done

### 2026-07-30 — Repair and extend MCP server configuration
- **Goal**: Get every configured MCP server connecting, and add the ones the repo's own
  `.claude/mcps/` docs described but never wired.
- **Output**: `fetch`/`time`/`git` fixed by pinning `mcp==1.29.0`; `git` repository
  argument dropped; `github` unblocked via `GITHUB_TOKEN`; `figma`, `sentry`, `notion`,
  `linear` added to `.mcp.json` and `.vscode/mcp.json`. 18 of 19 servers connected.
- **Status**: Done

### Make the layer match the target workflow architecture

- **Status:** Done — 9/9 tasks, reviewed, `PASS: 42 check(s) green`. Moved to
  Completed below; the remaining checklist scope is a NEW unit and enters at
  `writing-plans`.
- **Goal:** The chain the user specified, running end to end: decompose into
  independent tasks, a workflow per task, plan in plan mode, Gate 1, execute
  with minimal diffs, verify, bounded retry, scoped sweep and review, a
  confirmed push, Gate 2, release, record.
- **Constraints:** Two lifecycle gates only — the push confirmation stays an
  operational safety check with no `<!-- GATE n -->` marker. The retry budget
  stays **class-aware** (`security 0, merge 2, transient 2, deterministic 3,
  unknown 3`), not flattened to 3. A skipped check is **named as skipped**,
  never counted as a pass. Nothing acquires `gh pr merge`. Every rule added is
  enforced by a test or a hook, not prose.
- **Input:** `main` @ `9a65137`, clean, 37 checks green, 0 open PRs.
  `tools/parallel_groups.py` (scheduler + the live `normalise` bug),
  `tools/loop.py` + `_hooklib.FAILURE_BUDGETS`, `tools/test_no_slop.py`
  (scopes `repo|layer|portability`), `.claude/agents/task-implementer.md`
  (`isolation: worktree`), `executing-plans/references/{using-git-worktrees,
  parallel-dispatch}.md`, `docs/plans/2026-08-10-adaptive-workflow.md`
  (small-vs-major veto rule, to be folded in).
- **Output:** a corrected scheduler; `tools/worktree.py` with a mandatory base;
  one *proved* parallel dispatch or a deleted claim; `tools/scope.py`; a change
  scope for `no-slop` and `code-review`; scoped test selection; minimal-diff
  enforcement; plan-mode wiring where `ExitPlanMode` replaces Gate 1's
  `AskUserQuestion`.
- **Done Checks:** `python tools/run_checks.py --tier all --require-test` exits 0
  and prints the suite count; `python tools/parallel_groups.py <this plan>` shows
  `.claude/settings.json` correctly serialised rather than schedulable; and one
  live two-agent dispatch whose worktrees are proved based on the working branch
  by `git merge-base --is-ancestor`, read from the tree rather than from an
  agent's report.
- **Out of Scope:** merging anything; branch protection (403 on this plan tier);
  an external chain driver (`tools/drive.py`) — deferred until the
  chain-continuity instrument has measured how often the chain actually breaks.

### Add `tools/delivery_check.py` — delivery facts, computed not asserted

- **Status:** Done — merged to `main` as PR #10; it has since blocked two of its
  own unsafe deliveries, which is the evidence it works.
- **Goal:** One script that computes seven delivery facts about a branch and its
  PR, reports them, and refuses to decide — in the shape of `resume.py`,
  `analyze.py` and `git_identity.py`.
- **Constraints:** Reports, never decides; **never merges, pushes or rebases**
  (`test_process_router.py` already fails anything acquiring `gh pr merge`).
  Exit `0` ready / `1` a check failed / `2` could not determine — and `2` is not
  `0`, because a check that could not run is unrun, not passed. IO behind a
  `gather_facts()` seam with an `offline` escape, decisions in a pure
  `evaluate(facts)` the tests drive directly, mirroring
  `git_identity.gather(root, offline=)` + `render()`. **Not** in the fast tier:
  it needs a network and a remote, and that tier gates every auto-commit in
  seconds.
- **Input:** `docs/specs/2026-08-09-delivery-preflight-design.md`;
  `tools/git_identity.py` (API seam), `tools/analyze.py` (injected-`exists`
  test pattern), `tools/resume.py`; `.claude/skills/delivering/SKILL.md`.
- **Output:** `tools/delivery_check.py`; `tools/test_delivery_check.py`; a step
  in `delivering` that runs and quotes it; an entry in
  `.claude/project-checks.json` only if it proves fast enough to belong.
- **Done Checks:** `python tools/test_delivery_check.py` exits 0 with an
  assertion per check, each proved red first; and the base-alignment check flags
  a fixture where `merge-base(base, head) != tip(base)`, which is the case that
  stranded three merged units outside PR #7.
- **Out of Scope:** repo-settings-as-code (its own unit, and the only preventive
  option available); stacked-PR tooling such as Graphite (rejected in the spec);
  merging anything; configuring branch protection.

### Decide which capability owns layer retirement

- **Status:** Done — `capability-layer-maintenance` owns capability-layer audits, contract changes, migration, and retirement.
- **Goal:** Keep one owner for retiring or replacing capability-layer components.
- **Output:** Replaced `skill-authoring`, migrated active references, added hook-policy enforcement, and verified the complete suite.
- **Done check:** Skill routing, hook registration, hook policy, and the full all-tier suite pass.
- **Out of scope:** Product-code changes or project-history updates owned by `knowledge-manager`.

### Close the GOAL_CHECKLIST gaps that have an honest implementation

- **Status:** Done — 12/12 tasks, reviewed `passed: true`, `PASS: 49 check(s)
  green`. Branch `feat/checklist-completion`, local and unpushed.
- **Goal:** close every `GOAL_CHECKLIST.md` line with a real implementation
  here, and state plainly in the plan which lines have none.
- **Output:** nine tools (`chain`, `memory`, `worktree`, `halt`, `deps`,
  `git_ops`, `release_candidate`, `budget`, plus risk tiering in `scope`), two
  per-turn hooks, the gate log, and the release-candidate report Gate 2 reads.
- **Done Checks:** met — the full tier is green, rollback is executed rather
  than described (`True` in 0.4s, `'uninstall exited 1'` when disabled), and
  memory demonstrably changed this plan's Task 1.
- **Not verified:** Gate 2 has still never run end to end; the kill switch is
  proven in its suite but never mid-run; the meta-eval corpus has never been
  paid-run; three of four definition-of-done scenarios have never fired.
- **Out of Scope, and still out:** canary rollout, auto-rollback on production
  metrics, alerting, bake time, DAST — no running service exists. Gate 2
  auto-approve, refused on purpose.


# Tasks

## Active

<!-- Task(s) currently in progress. Overwrite in place as they change. -->

### Decide whether `/skills-doctor` still has a job

- **Status:** Not started — raised by a `no-slop` sweep on 2026-08-03
- **Goal:** Decide whether `/skills-doctor` is retired, narrowed, or kept as is.
- **Why now:** `tools/test_no_slop.py` and `tools/test_process_router.py` between
  them now cover the static half of what the command checks — description budget,
  YAML parse, `name:`/directory mismatch, loose `.md` files. Three owners of one
  question is the Duplicate Knowledge smell, and the routing keyword
  "skill layer health" already points at `no-slop` rather than at the command
  whose own description uses that exact phrase.
- **The part that is NOT duplicated,** and the reason this is a decision rather
  than a deletion: `/skills-doctor` compares the files on disk against what
  **actually rendered in the live session's skill listing**, which is truncated
  against a token budget. No file-reading script can see that. A skill can be
  valid on disk and absent from the listing on the exact turn that needed it —
  that has happened here.
- **Done check:** either the command is deleted and `CLAUDE.md`'s command list
  updated, or its text is narrowed to the live-listing measurement with the
  static checks removed and a pointer to the suites that own them.
- **Out of scope:** changing what the suites check. They are green and correct.

### Decide which capability owns layer retirement

- **Status:** Done — `capability-layer-maintenance` owns capability-layer audits, contract changes, migration, and retirement.
- **Goal:** Keep one owner for retiring or replacing capability-layer components.
- **Output:** Replaced `skill-authoring`, migrated active references, added hook-policy enforcement, and verified the complete suite.
- **Done check:** Skill routing, hook registration, hook policy, and the full all-tier suite pass.
- **Out of scope:** Product-code changes or project-history updates owned by `knowledge-manager`.
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

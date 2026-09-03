# Handoff

<!-- session-context:start -->

## Resume here

**Branch `docs/tech-resource-rules`** (commit `f00e8c0`, base `main` at
`9a79a6a`) is committed, not pushed, no PR. 5 new path-scoped
`.claude/rules/*-resources.md` + `docs/research/2026-09-03-tech-resources.md`
+ single-hop wiring into 8 files. `run_checks.py --tier all` `PASS: 63`.
Next: `documentation` already done for this unit → `release-git` for
branch + PR + merge on the user's explicit approval.

**Open, not started — layer-wide cross-reference mesh audit.** User asked
(2026-09-03) that every wirable rule/policy in `.claude/` be cross-linked
into a clean mesh — `.claude/policies/` (budgets, escalation, permissions,
security), `contracts/`, `adapters/`, `portability/`, `constitution.md`,
`operating.md`, `workflow.md`. This is its own `capability-layer-maintenance`
+ `refactoring` unit; needs a plan, not an improvised sweep.

**PR #47** (frontend depth) merged `d0b3424`. `main` is at `9a79a6a`.

## Decisions (don't relitigate)

- `install.py` ships the four load-bearing MCP servers from a **curated
  `templates/mcp-servers.json`**, merged into a target's `.mcp.json` by name,
  never overwriting. The 14-server dev `.mcp.json` is not the payload source —
  same reason as `CODEOWNERS.seed`.
- `.mcp.json` ↔ `.vscode/mcp.json` sync is enforced by `check_config_json.py`,
  not left to hand-discipline.
- Two approval gates only (`ExitPlanMode`, `AskUserQuestion`); branch-per-
  parallel-task is the standing default.

## Blocked / needs a human

nothing

<!-- session-context:end -->

## Known open items (not blocking)

- **`SHIPPED_MCP_SERVERS` is duplicated** as a literal in `.claude/install.py`
  and `.claude/hooks/check_config_json.py`. Routed to planning: needs a
  single-source mechanism (shared import, a test asserting equality, or
  deriving one from the seed). A synchronized shrink of both drifts silently
  past the stray-server check.
- `ISSUES.md` carries two `0x08` bytes in the entry describing `0x08` bytes —
  see `ISSUES.md` 2026-08-11 21:15.
- `tools/resume.py`'s `BRANCH_PREFIX` strips only `feat/` while
  `_hooklib.active_plans()` strips five prefixes — `resume.py` can't resolve
  a plan on a `fix/`|`docs/`|`chore/`|`refactor/` branch. Its own unit.
- The "five state reporters" overlap (`/wip`, `/git-state`, `/handoff`,
  `resume.py`, `03-state-report.py`) — folding `/git-state` into `/wip` was
  tried and reverted; the bodies don't overlap. Needs its own decision.
- Gate 2 (`AskUserQuestion` shipment approval) has still never fired end to
  end — this unit had no deploy target, so release stopped at the PR.

## Ruled out

- A dedicated lazily-read task-archive file the hook consults — a junk
  drawer nothing on the hot path reads; `LOG.md` + `docs/plans/` + git
  already answer "what shipped, when".
- Branch protection on this repo tier — `403 Upgrade to GitHub Pro`.
- Filtering the dev `.mcp.json` at install time instead of a curated seed —
  ships a misleading 14-server file in the wheel.

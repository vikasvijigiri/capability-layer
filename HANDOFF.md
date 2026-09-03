# Handoff

<!-- session-context:start -->

## Resume here

**Branch `docs/engineering-standards-frontend-depth`** (wip checkpoint
`3fc4e01`, base `main` at `ba9753e`) carries the engineering-standards
frontend rewrite + `.claude/rules/` wiring: 4 files, `run_checks.py --tier
all` `PASS: 63`. Not committed cleanly (only a wip checkpoint), not pushed,
no PR. Next: a clean commit + `/publish` when the user approves, or fold the
237-line `frontend-standards.md` into `references/frontend/*.md` topic files
first if they want it shorter. Plan: `~/.claude/plans/lazy-moseying-treehouse.md`.

**PR #46** (`feat/portable-mcp-wiring`, `8756550`) merged as `ba9753e` — the
prior "resume here" is done. `main` is at `ba9753e`.

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

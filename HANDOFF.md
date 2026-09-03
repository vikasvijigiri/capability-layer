# Handoff

<!-- session-context:start -->

## Resume here

Nothing in flight. **PR #47** (engineering-standards frontend depth + rule
wiring, commit `5f99764`) merged as `d0b3424`; branch deleted, local `main`
fast-forwarded. CI green on the SHA before merge, `mergeStateStatus CLEAN`.

Open follow-up (not blocking): `references/frontend-standards.md` is 237
lines — if it grows again, split into `references/frontend/*.md` topic files
with a nav table in `SKILL.md`.

**PR #46** (`feat/portable-mcp-wiring`, `8756550`) merged as `ba9753e`.
`main` is at `d0b3424`.

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

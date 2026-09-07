# Handoff

<!-- session-context:start -->

## Resume here

**Compact plan format for `task-analysis`** is built and verified on branch
`feat/compact-plan-tier`, **not committed or pushed**. Next action: commit the
four changed paths, then open a PR (risk `low` per `scope.py`, but
`.claude/skills/` change — code-review + a refactoring sweep before merge).

- Changed: `.claude/skills/task-analysis/references/plan-format.md` (rewritten
  two-section → one compact shape), `.claude/skills/task-analysis/SKILL.md`
  (C2–C4), `tools/test_analyze.py` (`COMPACT` fixture). New:
  `docs/plans/2026-09-07-compact-plan-tier.md`,
  `decisions/2026-09-07-one-plan-shape-all-risk-tiers.md`.
- `docs/research/2026-09-05-task-analysis-world-class-comparison.md` is also
  untracked (the prior-art comparison this unit rests on) — commit it too.
- `python tools/run_checks.py --tier all --require-test` → `PASS: 63`, exit 0.

**Deferred follow-up unit (not started):** same shift-left for skill/agent
frontmatter budgets (`new_skill_check.py` — description ≤700, ≥6 triggers).
Needs one canonical budget location the guide + template point at, not a 4th
copy — `test_process_router.py:73` forbids duplicate budget tables.

## Decisions (don't relitigate)

- **One plan shape at every risk tier** — 6-line brief, four-field tasks,
  90-line hard cap. Beat a two-tier split keyed to `scope.py --plan`. See
  `decisions/2026-09-07-one-plan-shape-all-risk-tiers.md`.
- `install.py` ships the four load-bearing MCP servers from a **curated
  `templates/mcp-servers.json`**, merged by name, never overwriting.
- `.mcp.json` ↔ `.vscode/mcp.json` sync is enforced by `check_config_json.py`.
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

# Tasks

## Active

<!-- Task(s) currently in progress. Overwrite in place as they change. -->

## Completed

<!-- Append-only, newest entry at the top. Never delete or rewrite an
entry here -- this is the full task/accountability trail for this repo,
from day one. Move a task here the moment it reaches a terminal Status. -->

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

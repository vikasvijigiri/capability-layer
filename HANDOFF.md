# Handoff

<!-- Current-state snapshot. Overwrite in place each time it's updated --
this is status, not history (that's LOG.md and TASK.md's Completed section). -->

## Completed

<!-- Append-only history. Deliberately OUTSIDE the session-context markers
below -- SessionStart never re-injects this, same as TASK.md's own Completed
section. Read the file directly when full history is actually needed. -->

- 2026-07-30 — MCP config repaired and extended; 18/19 servers connected.
- 2026-07-30 — `.claude/hooks/` wired into Claude Code lifecycle events, first via an
  adapter, then rewritten to direct registration (adapter deleted).
- 2026-07-30 — `git init`; branch guard and turn-checkpoint hooks added; `/save` command.
- 2026-07-30 — Global `~/.claude` layer removed and promoted into this repo; capability
  router hook added; registries made fully generated.
- 2026-07-30 — All 46 capability skills migrated to `.claude/skills/` with `<domain>-`
  prefixes. 61 skills now discoverable.

<!-- session-context:start -->
## Current Work

None active. Last unit of work (hook wiring) is in `TASK.md` under Completed.

## Pending

- Repo has **no commits yet**. Until an initial commit exists,
  `post-run/03-checkpoint.py` logs `unborn HEAD` and skips — the safety net is not
  active. Note the repo is now ~61 skills and 22 hook scripts of uncommitted work.
- Discoverable skill descriptions now cost roughly **6k tokens per turn** (46 capability
  + 15 process). That was a deliberate trade for reliable triggering; revisit with
  `context-economy-audit` if context pressure shows up.
- `claude.ai Slack` connector still needs OAuth (the 1 of 19 not connected).
- `linear`, `notion`, `sentry` are wired in `.mcp.json` but have no `.claude/mcps/` doc —
  surfaced by `mcps.json`'s `wired_but_undocumented` field.
- `.claude/mcps/figma-mcp.md` describes a PAT-based config; the wired server uses the
  OAuth remote endpoint. Doc is stale.

## Next Steps

- Make the initial commit to activate checkpointing (branch guard exempts it).
- Decide whether `on-human-approval-request` should move from `Notification` to the more
  precise `PermissionRequest` event.

## Open Questions

- Two hooks remain unverified against the live harness, passing only in suites:
  `pre-commit` (needs a real `git commit` to intercept) and the `permission_prompt`
  matcher on `Notification` (no permission prompt has occurred while it was registered).
- The 46 migrated skills have never been invoked. Their descriptions are inherited from
  the capability files and are untested as trigger surfaces — expect to tune wording
  once real prompts start routing to them.
<!-- session-context:end -->

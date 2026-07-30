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
- 2026-07-31 — Initial commit `4069f4b`. `.gitignore`'s blanket `.claude` rule fixed.
- 2026-07-31 — `.claude/capabilities/` removed; routing collapsed into
  `.claude/routing/capabilities.md`. 86 skills, each with a phase-based `model:`.

<!-- session-context:start -->
## Current Work

None active.

## Pending

- **The skill listing is truncated against a token budget.** 86 descriptions total
  ~13k tokens; measured on 2026-07-31, ~36 rendered (~5.7k) and 47 arrived as bare
  names with no trigger surface. Which half renders varies between turns, so a skill
  can be untriggerable on the turn that needed it. This is why the keyword router is
  load-bearing rather than redundant. Run `context-economy-audit` to cut description
  length — note it now says adding trigger phrasings and staying in budget are in
  direct conflict past this point.
- `claude.ai Slack` connector still needs OAuth (the 1 of 19 not connected).
- `linear`, `notion`, `sentry` are wired in `.mcp.json` but have no `.claude/mcps/` doc —
  surfaced by `mcps.json`'s `wired_but_undocumented` field.
- `.claude/mcps/figma-mcp.md` describes a PAT-based config; the wired server uses the
  OAuth remote endpoint. Doc is stale.

## Next Steps

- Run `context-economy-audit` on the skill descriptions — the truncation above is now
  the highest-cost problem in the repo.
- Frontend still has no runtime-performance skill; `frontend-bundling-helper` covers
  bundle bytes only, not LCP/CLS/INP or re-render cost.
- Decide whether `on-human-approval-request` should move from `Notification` to the more
  precise `PermissionRequest` event.

## Open Questions

- One hook remains unverified against the live harness: the `permission_prompt` matcher
  on `Notification` (no permission prompt has occurred while it was registered).
  `pre-commit` is now verified — it blocked the initial commit twice, on AI attribution
  and on a planted-secret fixture, and both were real.
- Deleting `.claude/capabilities/backend/spec.md` dropped ~52 lines of backend
  conventions that nothing referenced and that partly described infrastructure which
  does not exist (a "repo telemetry integration" on topic `backend.*`). If any of it was
  wanted, it is in `4069f4b`.
- Most of the 86 skills have still never been invoked; their descriptions remain
  untested as trigger surfaces, and half are truncated away on any given turn.
<!-- session-context:end -->

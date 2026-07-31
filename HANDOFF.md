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
- 2026-07-31 — Human-approval gates wired: `approval-brief` owns the dialogue, 9 skills
  route to it. `mvp-builder` made capable of building. 12 agents given `model:`.

<!-- session-context:start -->
## Current Work

**105 files uncommitted on `collapse-capabilities-into-routing`** — approval gates, the
`mvp-builder` rewrite, three commands, agent `model:`, `pre-run/04-docs-staleness.py`, the
`PermissionRequest` fix, frontmatter fill (`effort`/`argument-hint`/`context`), and
read-only enforcement on six skills. All verified — three suites green, 86 skills and 12
agents parse clean, registries deterministic — but none of it is in git.

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

- Commit the working tree. It is verified but unrecorded in git.
- Run `/skills-doctor` or `context-economy-audit` on the descriptions — 86 skills at
  ~13.5k tokens plus 12 agents at ~1.9k, against a listing that renders roughly 5.7k.
  Highest-cost problem in the repo.
- Frontend still has no runtime-performance skill; `frontend-bundling-helper` covers
  bundle bytes only, not LCP/CLS/INP or re-render cost.
- Decide whether `post-run/04-docs-sync.py` should drop `.claude` from its `noise_dirs`.
  `pre-run/04-docs-staleness.py` now covers the gap, so this is cleanup, not a fix.
- Decide whether `on-human-approval-request` should move from `Notification` to the more
  precise `PermissionRequest` event.

## Open Questions

- **All hooks are now verified against the live harness.** `pre-commit` blocked the
  initial commit twice (AI attribution, planted-secret fixture), and
  `on-human-approval-request` was found registered on the wrong event entirely and moved
  to `PermissionRequest` — see LOG.md 2026-07-31 07:30.
- How many *other* hooks are wired to events that never fire? Audited on 2026-07-31 and
  none found, but the method has a known blind spot: the `session_id` test only reaches
  hooks that log the **raw** payload. `01-secret-scan.py`, `03-checkpoint.py` and
  `01-env-check.py` log derived data and came back as false positives despite being
  provably alive. A hook that both logs derived data *and* is wired wrong would still be
  invisible.
- Does the `agent:` frontmatter field actually dispatch a subagent? Unverified — it is
  supported and parses, but no skill uses it. Proving it on one skill is the prerequisite
  for declarative parallel fan-out, and would be done the same way `PermissionRequest` was.
- Deleting `.claude/capabilities/backend/spec.md` dropped ~52 lines of backend
  conventions that nothing referenced and that partly described infrastructure which
  does not exist (a "repo telemetry integration" on topic `backend.*`). If any of it was
  wanted, it is in `4069f4b`.
- Most of the 86 skills have still never been invoked; their descriptions remain
  untested as trigger surfaces, and half are truncated away on any given turn.
<!-- session-context:end -->

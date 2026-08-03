# Handoff

<!-- Current-state snapshot. Overwrite in place each time it's updated --
this is status, not history (that's LOG.md and TASK.md's Completed section). -->

## Completed

<!-- Append-only history. Deliberately OUTSIDE the session-context markers
below -- SessionStart never re-injects this, same as TASK.md's own Completed
section. Read the file directly when full history is actually needed. -->

- 2026-08-01 — Capability layer collapsed to three skills and committed at
  `1443ba2`. Prior history reset here; `git log` from that commit back.
- 2026-08-04 — Hooks decoupled from skills: the prompt router, two nudge hooks,
  a duplicate installer hook and the keyword routing table deleted. See
  `decisions/2026-08-04-hooks-never-name-a-skill.md`.

<!-- session-context:start -->
## Current Work

**Branch `collapse-capabilities-into-routing`, 65 commits, nothing pushed.** One
uncommitted path (`.claude/settings.json`). 8/8 suites, `mypy` (24 files) and
`ruff` green.

**Hooks and skills are now independent.** 10 hooks over 7 events, every one of
which acts, denies or measures. No hook names a skill in anything it emits, and
`tools/test_hook_registration.py` fails if one does — negative-tested. The
reasoning and the rejected alternative are in
`decisions/2026-08-04-hooks-never-name-a-skill.md`.

**`session-start/03-state-report.py` is the replacement signal.** It measures
commits since `LOG.md`/`HANDOFF.md`/`ISSUES.md` last changed and `.claude/` files
changed since the branch point, then renders `workflow.md`'s `[state:<key>]`
blocks. No state file — counts come from `merge-base..HEAD` plus the worktree, so
landing the branch resets them.

**Skills trigger from `description:` alone.** There is no keyword router. All 13
descriptions carry a `Do NOT use` clause and sit under the 500-char cap.

## Pending

- **`03-state-report.py` has never fired in a real `SessionStart`.** It was added
  after this session started. Next session start is its first live run, and given
  current counts it should open with both `[state:*]` blocks. If it is silent,
  that is the bug.
- **`reloadSkills: true` is emitted but unproven.** `global-session-start/01-layer-bootstrap.py`
  sets it on install so the installing session can use the skills it just wrote.
  The field is documented; only a real install-then-use session proves it works.
- **No skill has been run end to end under the Iron Law** (a baseline pressure run
  *without* the skill) except `code-review`, `task-brief`, `no-slop` and
  `knowledge-manager`. Unchanged, and still the largest standing risk.
- **`releasing` cannot be dogfooded here — no deploy target.** Unchanged.
- **Two open `ISSUES.md` entries** from 2026-08-03: the layer installer written
  twice (still true — `global-session-start` and the deleted `on-repo-create`
  shared logic; only one survives now, so this may be closable on re-read), and
  every install target receiving a hook that cannot fire there.
- **`/wip` and `/git-state` overlap** — same git data, two command files, 10KB.
  The only merge candidate found in the `.claude/` audit.

## Next Steps

1. **`code-review` over the branch.** 65 commits, unreviewed, and today alone
   changed 55 files (+3830/-1000). This gates `delivering`.
2. **Restart a session to prove `03-state-report.py` fires.** Cheapest outstanding
   verification and it closes the largest untested claim.
3. Re-read the two 2026-08-03 `ISSUES.md` entries — the installer-duplication one
   probably resolved when `on-repo-create` was deleted.

## Open Questions

- **Is the `[state:<key>]` table worth its machinery at two states?** It earns its
  place in Trellis because many task statuses have genuinely different next steps.
  Here it buys the consequence landing with the fact at session start. If it grows
  past three or four keys without the states differing, reconsider.
- **Nothing recovers the description-truncation backstop.** The keyword table was
  it. `skillListingMaxDescChars` / `skillListingBudgetFraction` are the only
  levers; neither has been tried.
- Several claude.ai connectors (Asana, Atlassian, Box, Canva, HubSpot, Intercom,
  monday.com) need OAuth and cannot be authorised from a non-interactive session.
<!-- session-context:end -->

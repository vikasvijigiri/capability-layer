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

**Branch `rebuild-capability-layer`, 68 commits, nothing pushed.** 8/8 suites,
`mypy` (24 files) and `ruff` green.

**REVIEWED AND SIGNED OFF — 2026-08-04, by the user, on the whole branch.**
Renamed from `collapse-capabilities-into-routing` during the review: `routing`
matched zero changed paths, because `.claude/routing/` was deleted. Two findings
were raised and fixed before sign-off — `pre-edit`/`pre-deploy` had no test
coverage at all despite being deny hooks whose failure mode is silent permission,
and `03-state-report.py`'s `base_commit()` fell through to the root commit on the
default branch, reporting the entire history as one branch's work.

One risk was accepted rather than fixed: `global-session-start/01-layer-bootstrap.py`
writes 54 files into any git repo root with no `.claude/`, including one you merely
`cd`'d into. Four refusals bound it; that is the chosen behaviour.

Not read during the review, stated so it is not mistaken for covered: the 60
`docs/` files, `docs/archive/` in full, the 13 `SKILL.md` bodies end-to-end, and
the earlier three days' commits individually — their net effect on the current
tree was reviewed, not each commit.

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
- **`PLAN.md` was deleted on 2026-08-04.** An unfilled template in four days of
  heavy use, and two skills disagreed about who owned it. `writing-plans` keeps
  writing dated `docs/plans/` files. If a programme-level artefact is ever wanted
  it should be its own skill.

## Next Steps

1. **`delivering` is now unblocked** — the branch is reviewed and signed off.
   Nothing is pushed and there is no remote; `delivering` owns that route and has
   its own approval gate.
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

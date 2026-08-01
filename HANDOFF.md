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
- 2026-08-01 — `brainstormer` rebuilt on the `obra/superpowers` shape; new `writing-plans`
  skill adopted from the same source. 87 skills. Direction set: tear the capability layer
  down to these two skills plus hooks, and rebuild from superpowers and other repos.
- 2026-08-01 — First `brainstormer` run end to end. Spec approved and committed:
  `docs/specs/2026-08-01-evidence-ledger-design.md`. Next: `writing-plans`.

<!-- session-context:start -->
## Current Work

**Teardown done, uncommitted.** 182 deletions, 12 modifications, 0 untracked.
`.claude/` is now `skills/` (`brainstormer`, `writing-plans`), `hooks/`, `routing/`,
`commands/` and the two settings files. Safety commit `eaab430` holds everything
that was removed.

All checks green and actually run: four suites pass (`All hook tests passed`,
`All process-router tests passed (2 entries routed)`, `All docs-gate tests passed`,
`All docs-staleness tests passed`), `01-env-check.py` reports `{"issues": []}` and
was proved to detect a planted unrouted skill, frontmatter parses `2 skills;
problems: none`, hook registration has no dangling paths in either direction,
`compileall` exits 0.

**Not committed** — the safety commit was approved, this was not.

## Pending

- **Six hooks name skills that no longer exist, in user-visible output.**
  `post-run/04-docs-sync.py:304`, `post-run/05-docs-gate.py:110`,
  `pre-commit/05-docs-required.py:107` and `pre-run/04-docs-staleness.py:164,205`
  say "invoke `knowledge-manager`"; `pre-commit/03-review-gate.py:184,195,204` and
  `04-delivery-guard.py:293` say "run `code-review`". Both skills were deleted.
  The Stop gate blocked a turn on this within minutes of the teardown. Nothing
  checks whether a hook's named skill exists.
- **`04-delivery-guard.py` false-positives on Windows paths.**
  `find_ai_attribution` scans the whole command string and `_STANDALONE` excludes
  `/` but not `\`, so any path containing `\claude\` is read as AI attribution. It
  denied two legitimate commits. Fix: add `\\` to both lookaround character classes.
- **The 500-token skill-response cap contradicts both surviving skills.** CLAUDE.md
  caps every skill response at 500 tokens; both present design in 200-300 word
  sections across three gates and emit full code blocks. Kept deliberately when the
  option to drop it was offered. No automated check can catch this.
- **`docs/specs/` and `docs/plans/` do not exist yet.** Both skills write there.
- `docs/architecture/` (00-17) documents the deleted layer in detail and was left
  untouched. Rebuild or delete; do not trust it.
- `on-blueprint-promote/02-git-tag.py` is unregistered and fires on a concept that
  no longer exists. Inert, not wrong — unlike the nudge that was removed.
- `claude.ai Slack` connector still needs OAuth (the 1 of 19 not connected).

## Next Steps

- Commit the teardown.
- Fix the six hook strings above, then decide whether a check should assert that
  every skill name appearing in a hook's output resolves to a real skill directory.
  That check is what would have caught all six, and the five earlier instances.
- Rebuild from superpowers: `subagent-driven-development` and `executing-plans` are
  what `writing-plans` should hand off to, and neither exists here.
- `/skills-doctor` measures description budget across the skill layer. With two
  skills it has almost nothing to measure — decide whether it earns its place.

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
- `changed_files()` is duplicated verbatim across `pre-run/04-docs-staleness.py` and
  `post-run/05-docs-gate.py`, with a third near-copy in `pre-commit/05-docs-required.py`.
  `_hooklib.py` is where it belongs. Raised by code-review 2026-07-31 and deliberately
  deferred; two copies of one behaviour means the stale one eventually wins.
- Does `decision: block` on `Stop` work in this build? 132 payloads, zero blocks ever.
  `post-run/05-docs-gate.py` and `04-docs-sync.py` both depend on it. It will verify
  itself the first time 10+ files go stale at turn end.
- Does the `agent:` frontmatter field actually dispatch a subagent? Unverified — it is
  supported and parses, but no skill uses it. Proving it on one skill is the prerequisite
  for declarative parallel fan-out, and would be done the same way `PermissionRequest` was.
- **The deleted layer is recoverable but only from git.** 85 skills, 12 agents, 6
  blueprints, 7 workflows, 11 validators, 1 playbook, 1 template and 27 MCP docs live in
  history from `4069f4b` through the safety commit. Nothing else holds a copy.
- Neither surviving skill has ever been run end to end. Their gates, handoffs and file
  paths are asserted by their own text and by nothing else — the same "prose declares a
  capability the wiring does not implement" class this repo has hit five times.
- `writing-plans` hands off to `backend-engineer`, `frontend-engineer`, `ai-engineer`,
  `qa-engineer`, `work-decomposition` and `workflow-orchestrator`. **All six are being
  deleted.** Its execution handoff points at nothing until the rebuild supplies
  replacements.
<!-- session-context:end -->

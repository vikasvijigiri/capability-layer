---
description: Where was I — branch, uncommitted work, and which knowledge docs have gone stale relative to the actual diff
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

Mode: read-only
Arguments: optional focus hint in `$ARGUMENTS` such as `docs` or `git`.

Answer "where was I" from the repo's real state, not from memory of the
conversation. Read-only; this command never edits, stages, commits or pushes.

Report:

1. **Position.** Current branch, whether it is a protected one (`main`, `master`,
   `develop`, `release` — the branch guard denies commits there), how far ahead of
   the base branch, and the last three commit subjects.

   **Detect the base; never assume `main`.** A repository's base has been
   `master` while the session banner said `main`, and `git merge-base HEAD main`
   then fails outright. `/git-state` §1 owns the detection and the commands
   behind every number — run it rather than restating it here. This command
   judges; that one counts, and the split is the reason both exist.

2. **Uncommitted work.** `git status --porcelain` and `git diff --stat`. Group the
   changes by area (`.claude/skills/`, `tools/`, docs) rather than listing every
   path — a flat list of forty files is not a status. Call out anything staged but
   not committed separately from unstaged work.

3. **Doc staleness — the part worth having.** Compare what the diff actually
   touches against `TASK.md`, `HANDOFF.md` and `LOG.md`:
   - Does `HANDOFF.md`'s `Current Work` match what is uncommitted? A `HANDOFF`
     saying "none active" over a forty-file diff is stale, and stale is worse than
     empty because the next session trusts it.
   - Does `TASK.md` have an `Active` entry for this work, and is its status right?
   - Has `LOG.md` got an entry covering the uncommitted change?
   Report each as current or stale, with the specific mismatch.

4. **Blocked or pending.** `HANDOFF.md`'s `Pending`, `Next Steps` and
   `Open Questions`, plus any open entry in `ISSUES.md`. Say which are still real
   given the current state — an item resolved by the uncommitted work is itself a
   staleness finding.

5. **One-line answer.** Finish with a single sentence naming the next concrete
   action. Not "continue the work" — the actual next step.

Rules:

- Read-only. If docs are stale, say which ones and stop there; do not fix them as
  a side effect of asking where you were.
- Do not restate the conversation. This reads the repo; if the two disagree, the
  repo is right and the disagreement is the finding.
- If I passed an argument, treat it as a focus area (e.g. `docs`, `git`) and say
  what you skipped: $ARGUMENTS

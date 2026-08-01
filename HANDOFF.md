# Handoff

<!-- Current-state snapshot. Overwrite in place each time it's updated --
this is status, not history (that's LOG.md and TASK.md's Completed section). -->

## Completed

<!-- Append-only history. Deliberately OUTSIDE the session-context markers
below -- SessionStart never re-injects this, same as TASK.md's own Completed
section. Read the file directly when full history is actually needed. -->

- 2026-08-01 — Capability layer collapsed to three skills and committed at
  `1443ba2`. Prior history reset here; `git log` from that commit back.

<!-- session-context:start -->
## Current Work

Clean tree at `1443ba2` on `collapse-capabilities-into-routing`. Nothing in
flight.

## Pending

- **Nothing asserts that a name in a hook or skill resolves to something real.**
  22 dead references were cleared by hand at `1443ba2`; this is the repo's
  most-repeated failure and the only one with no automated guard. A check would
  grep `.claude/**` for backticked kebab-case tokens and `.claude/**` paths and
  assert each resolves. `tools/test_process_router.py` now does this for skill
  frontmatter only.
- **No skill has ever been run end to end.** Every gate, handoff and file path
  in the three SKILL.md files is asserted by its own text. The superpowers Iron
  Law — a baseline pressure run *without* the skill before writing it — is unmet
  on all three.
- **`04-delivery-guard.py` false-positives on Windows paths.**
  `find_ai_attribution` scans the whole command string and `_STANDALONE`
  excludes `/` but not `\`, so any path containing `\claude\` reads as AI
  attribution. Fix: add `\\` to both lookaround character classes.
- **`Stop` blocking is unproven in this build.** 130+ payloads, zero blocks.
  `post-run/05-docs-gate.py` and `04-docs-sync.py` both depend on it.
- **`changed_files()` is duplicated** across `pre-run/04-docs-staleness.py` and
  `post-run/05-docs-gate.py`, with a third near-copy in
  `pre-commit/05-docs-required.py`. `_hooklib.py` is where it belongs.
- **`docs/plans/` does not exist yet**; `writing-plans` writes there.
- **`docs/00-*.md … 17-*.md` describe the deleted layer.** Rebuild or delete;
  do not trust them.

## Next Steps

Nothing assigned. Pick from Pending.

## Open Questions

- Does the `agent:` frontmatter field actually dispatch a subagent? Supported
  and parses, but no skill uses it.
<!-- session-context:end -->

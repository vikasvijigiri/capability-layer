# Handoff

<!-- Current-state snapshot. Rewrite this file at each meaningful handoff;
history belongs in LOG.md and TASK.md's Completed section. -->

## Completed

The chain has now run end to end, once: spec → plan → execute → verify → sweep
→ review → deliver, with two recovery loops back to stage 3. `HANDOFF.md` said
"The chain has never completed once" until 2026-08-09; that is no longer true.

Three units landed as stacked pull requests. See `LOG.md` 2026-08-09 20:48.

<!-- session-context:start -->

## Current Work

Nothing in flight. Five PRs are open and **none is merged**:

| PR | Branch | Base |
|---|---|---|
| #7 | `merge-framing-into-planning` | `main` |
| #5 | `feat/uninstall-verb` | #7 |
| #6 | `fix/delivering-approval-gate` | #5 |
| #8 | `docs/session-2026-08-09` | #5 |
| #9 | `fix/unenforceable-claims` | #6 |

**Merge order: #7 → #5 → then #6 and #8 in either order → #9.** Each PR's
declared base is its actual branch point, verified — #6 was opened against #7
while cut from #5, which made it show all ten of #5's files; corrected to base
`feat/uninstall-verb` and it now shows three.

`TASK.md` `## Active` holds three older items, none of them today's work.

## Pending

- **Branch protection on `main` is unavailable, not merely unset.** The API
  answers `403 Upgrade to GitHub Pro or make this repository public` — neither
  protection nor rulesets are offered on a free private repository. This was
  carried here as an actionable task and it never was one.

  What holds the line instead: `.github/workflows/checks.yml` runs on every pull
  request and resolves the same `.claude/project-checks.json` the local gate
  does, so a red branch is **visible** on the PR; and
  `pre-commit/02-branch-guard.py` refuses commits on `main` in any tree with the
  layer installed. What is genuinely uncovered: nothing prevents a direct
  `git push` to `main` from a clone without the layer.

  A real decision, for a human: make the repository public, upgrade the plan, or
  accept the gap knowingly. `/publish` now probes and reports this rather than
  printing instructions that cannot be followed.
- **`ISSUES.md` 2026-08-09 (plan checkbox) — fixed in #9, entry still says
  Open.** `executing-plans` claimed `writing-plans` mandated `- [ ]` checkboxes;
  it did not, and zero existed across every plan. #9 makes the template emit a
  `## Progress` block, has `analyze.py` count the boxes against the task
  headings, and adds the check that closes the *class* — a consumer naming a
  syntax must have a producer that emits it. Update the `ISSUES.md` entry to
  Resolved when #9 merges.
- **Commit `154b66a` was pushed** and holds the pre-fix path-traversal state.
  Private repo, not rewritten — flagged in #5's body.

## Next Steps

1. Review and merge #7, then #5 and #6.
2. Configure branch protection on `main` before anything else lands.
3. Decide the plan-checkbox contradiction.

## Open Questions

- **Nothing carries the chain across a manual step.** Each skill's `## Next
  step` names its successor, and that is the only link — there is no engine
  tracking "stage 7 done, run stage 8". Doing a stage's work by hand, as
  happened with the push, severs it silently. A `Stop` hook could *report* the
  gap; it cannot invoke a skill, and
  `decisions/2026-08-04-hooks-never-name-a-skill.md` constrains what it may say.
- **Is mutation testing worth its cost given what it missed?** Eight mutations
  reported `hollow: none` on code carrying a path traversal, because every
  mutation assumed the manifest was trustworthy input. It proved the checks bite
  and said nothing about coverage of categories nobody considered.

<!-- session-context:end -->

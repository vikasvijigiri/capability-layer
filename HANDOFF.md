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

Nothing in flight. Branch `fix/delivering-approval-gate`, pushed. Three PRs are
open and **none is merged**:

| PR | Branch | Base |
|---|---|---|
| #7 | `merge-framing-into-planning` | `main` |
| #5 | `feat/uninstall-verb` | `merge-framing-into-planning` |
| #6 | `fix/delivering-approval-gate` | `merge-framing-into-planning` |

**#7 must land first** — the other two are stacked on it. #5 and #6 are siblings
and touch disjoint files. 39 files, +2580/-625 against `main`.

`TASK.md` `## Active` holds three older items, none of them today's work.

## Pending

- **Branch protection on `main` is still unconfigured.** No required checks, no
  merge queue. `/publish` prints the settings; an agent never sets its own merge
  gates, so this needs a human in the GitHub UI.
- **`ISSUES.md` 2026-08-09 (plan checkbox) is Open.** `executing-plans` says
  *"`writing-plans` mandates that syntax expressly"* about `- [ ]` checkboxes,
  and it does not — the task template emits `**Done when:**` and no checkbox.
  Zero task checkboxes exist across every plan in `docs/plans/`. Worked around
  by hand in one plan. The real fix is a decision about which file is wrong, and
  it belongs to `capability-layer-maintenance`.
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

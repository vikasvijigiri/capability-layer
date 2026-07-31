---
name: blueprint-promoter
model: opus
description: Decides when a solution has been repeated often enough to become a reusable blueprint, and promotes it. Use for "we keep doing this", "we have solved this before", "this is the third time", "make this reusable", "turn this into a pattern", "should this be a template", "promote this", "standardise how we do this". Prefer this over solving the same problem a fourth time from scratch - an unpromoted repeated solution is knowledge that leaves with the session. Do NOT promote on the first or second occurrence; two points are not a pattern.
effort: high
---

# Blueprint Promoter

`.claude/blueprints/` and the `on-blueprint-promote` hook already exist. This skill is what
decides a blueprint is warranted - without it, the machinery never fires.

## Promotion bar

Promote only when **all** hold:

1. **Solved at least three times.** Twice is coincidence. Cite the occurrences.
2. **The shape was materially the same each time** - same problem signature, same
   sequence, differing only in parameters.
3. **The variation is parameterisable.** If each instance needed genuinely different
   judgment, it is not a blueprint; it is a skill or nothing.
4. **A validator exists** for the resulting solution, or can be named. A blueprint that
   cannot be checked is a template for repeating a mistake faster.

Failing any of these, say so and stop. A premature blueprint is worse than none - it gets
followed.

## Steps

1. Write the **Problem Signature** first - the conditions under which this blueprint
   applies, and just as importantly when it does not.
2. Record **Preconditions** that must hold before it is used.
3. Write the **Solution Workflow** as steps referencing real skills by name, not prose.
4. Name the **required validator**, matching the owning capability.
5. Write to `.claude/blueprints/<domain>-<name>.md`, following the naming convention and
   the structure of an existing blueprint.
6. Fire the hook:
   `python tools/run_hook.py on-blueprint-promote '{"blueprint": {"name": "<domain>-<name>"}}'`
   Git tagging stays behind `ENABLE_GIT_TAG=1` - a tag on a shared repo is a side effect
   and must be opted into.
7. Add it to the owning capability's `index.md`, and to the `## Routing` section of the
   skills it now takes precedence over.

## Demotion

If a blueprint stops matching reality, say so and remove it. A stale blueprint outranks
fresh judgment by default, which is exactly when it does damage.

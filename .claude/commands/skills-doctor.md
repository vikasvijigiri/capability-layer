---
description: Measure the skill layer — description budget and truncation, YAML breakage, name mismatches, missing model — with real numbers
---

Diagnose the skill layer. Every check here corresponds to a failure that has
actually happened somewhere, not a hypothetical one. Measure; never estimate.

Set `PYTHONIOENCODING=utf-8` before running anything that prints skill text.

Report, in this order:

1. **Description budget — the headline.** Total `description` characters across
   all `.claude/skills/*/SKILL.md`, and that figure divided by 4 as an approximate
   token count. Then compare against what actually rendered in the current session's
   skill listing: count how many skills arrived with a description versus as a bare
   name. The listing is truncated against a budget, so a skill can be untriggerable
   on the exact turn that needed it — a skill has looked broken for this reason
   while being perfectly valid. Name the ten longest descriptions, since
   those are the lever.

2. **YAML breakage.** Parse each frontmatter block with a strict parser. Report any
   that fail, and any where the result is not a mapping. Specifically flag `: "`
   anywhere in a `description` — colon-space-quote makes an unquoted scalar parse
   as a mapping and the description silently vanishes, leaving the skill listed but
   untriggerable. This has silently broken a real skill more than once.

3. **Discovery shape.** Claude Code only finds `.claude/skills/<name>/SKILL.md`
   where the frontmatter `name:` equals the directory name. Report any mismatch,
   and any `.md` sitting loose in `.claude/skills/` rather than in its own folder.
   Both are silently invisible — no error, the skill just does not exist.

4. **Missing fields.** Any skill with no `model:`, or an empty `description`.
   Report the model split (opus / sonnet / haiku) against the intended rule:
   opus up to and including planning, sonnet for implementation, haiku for testing
   and deployment. Flag anything that looks misfiled.

5. **Reachability.** Every skill must have a `## <name>` entry in
   each skill's `description:`, and every entry there must name a real
   skill directory. With the capability router gone this file is the only routing
   signal that survives listing truncation, so an unrouted skill is invisible on
   any turn its description is truncated away.

6. **Dangling references.** Names a skill's body hands off to — other skills,
   agents, commands, file paths it writes to — that do not exist. A teardown that
   removes skills or agents leaves handoffs naming them behind, and that is dead
   text which reads as a working path.

Report findings most-actionable first, each with a `file:line` where one applies,
what is wrong, and a one-line fix. A byte count on its own is not a finding — say
why it matters.

Rules:

- **Report only. Change nothing.** Fixes are a separate, explicit follow-up I
  approve per finding.
- Measure by reading files and running commands, never from memory of what the
  repo looked like earlier.
- If I passed an argument, scope the report to it (e.g. `budget`, `yaml`,
  `orphans`) and say which sections you skipped: $ARGUMENTS

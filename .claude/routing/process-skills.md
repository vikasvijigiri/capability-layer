# Process-Skill Routing

Keyword routing for the skills in `.claude/skills/`. Read by
`.claude/hooks/pre-run/05-process-skill-router.py`, which scans every prompt and
injects the names of any skills that match.

Why this file exists: the skill listing is truncated against a token budget, so
a skill's `description:` — its only other trigger surface — can be absent on the
exact turn it was needed. This file is the routing signal that survives that
truncation. It is currently cheap to satisfy (two skills), and the budget is a
constraint on what gets added back, not a problem to solve later.

**Format contract.** One `## <skill-name>` heading per entry, matching a
directory under `.claude/skills/` exactly. Exactly one `Keywords:` line beneath
it, comma separated. `tools/test_process_router.py` asserts every heading
resolves to a real skill and that no skill is left unrouted.

**Keyword style — phrases, not words.** Naming a specific skill is a strong
claim, so entries lean on multi-word phrases lifted from each skill's own
`description:` trigger list rather than bare words that fire on anything.

---

## task-brief

Keywords: task brief, six line brief, 6 line brief, scope this, scope the task, break this into a brief, structure this task, turn this into a task, write the brief, what is out of scope, add support for, can we support, i want users to be able to, it would be nice if, new feature request

## brainstormer

Keywords: brainstorm, spitball, bounce ideas, any ideas, what could we do, throw some ideas, thinking out loud, give me some angles, what are our options, help me think this through, i am stuck, im stuck, what if we, ideate, riff on

## writing-plans

Keywords: implementation plan, write the implementation plan, turn the spec into tasks, plan the tasks, break the spec into steps, bite-sized tasks, task by task plan, hand this to a subagent

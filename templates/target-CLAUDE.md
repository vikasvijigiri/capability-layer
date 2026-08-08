# CLAUDE.md

## Project overview

State what this project is, who it's for, and what it optimizes for — two to
three sentences, no more. This file is the bootloader for the capability layer
installed into `.claude/` and `tools/` at this repo's root: skills, lifecycle
hooks and slash commands that enforce a spec → plan → build → verify workflow.
Fill in the project description above; everything below describes the layer
itself and should stay accurate as this repo changes, not as the layer's
source repository changes.

---

## Tech stack

List only what changes how Claude should write code here — not everything
installed.

- **Language(s):** [language + version]
- **Framework(s):** [framework + version]
- **Package manager:** [npm / pip / cargo / etc.]
- **Database:** [if applicable]
- **Testing:** [test runner and how tests are organized]
- **Lint / format:** [tool(s), and whether they run automatically]

---

## The workflow this layer enforces

`.claude/workflow.md` owns the stage order and what each stage consumes and
produces — read it rather than inferring an order here. Skills trigger from
their own `description:` frontmatter; nothing routes them.

**There are exactly two human approval gates**, and no other step may ask for
a third:

1. **The finished plan**, at the end of the planning stage, before execution
   starts.
2. **Shipment approval**, before a release candidate goes to a deploy target.

Both are asked as an explicit choice, never inferred from prose. A rejection
of either gate is durable: it is recorded against the artifact rather than
silently retried.

## Commands

    python tools/run_checks.py --tier all --require-test   # canonical: run before any completion claim
    python tools/resume.py            # which state this unit of work is in
    python tools/loop.py              # what the escalation ladder says to do next
    python tools/run_hook.py <event> '<json-payload>'   # fire one hook manually

**Run `/verify` (or `python tools/run_checks.py --tier all --require-test`)
before claiming any work is done.** Set `PYTHONIOENCODING=utf-8` before
running any tool script, or non-ASCII output can raise `UnicodeEncodeError`
and turn a passing run into a fake failure.

Checks come in two tiers, because their cost differs by an order of magnitude:

| Tier | Kinds | Runs |
|---|---|---|
| fast | lint · typecheck · test | every turn, seconds |
| slow | build · audit · e2e · smoke | before delivery, minutes |

The fast tier gates the auto-commit below; the slow tier gates delivery and
release, and runs in CI so it cannot drift from local.

---

## Code style

State conventions that aren't already enforced by a linter.

- Import style: [e.g. named exports only, ES modules not CommonJS]
- File/naming conventions: [e.g. test files live next to source as `*.test.ts`]
- Patterns to follow / avoid: [project-specific conventions]

---

## Project structure

A map of where things live, not a restatement of every file.

| Path | What it is |
|---|---|
| `.claude/skills/` | the workflow's skills, one directory each |
| `.claude/hooks/` | lifecycle hooks that act, deny, or measure |
| `.claude/settings.json` | what fires in this repository |
| `.claude/commands/` | slash commands |
| `tools/` | the checks, the state resolver, and the escalation ladder |
| `[path]` | [what lives here and why it's separate] |

---

## The commit loop

Commits made by the layer's automation are local-only and checkpoint-shaped,
never a substitute for review. A post-run hook commits what changed at the end
of a turn, as a `wip:` checkpoint, only when the change is small, contains no
secret, and the fast tier is green. **It never pushes**, and never stages
everything indiscriminately. Review happens over the whole branch before
delivery, not per checkpoint.

## Workflow rules

Process the team follows that isn't already enforced by a tool.

- [e.g. open a draft PR before starting non-trivial work]
- [e.g. commits should be scoped to one logical change]
- If a rule here is instead enforced by a hook, script, or CI check, say so
  and point at it rather than duplicating the rule in prose.

---

## Never

- Never report a check as passing unless it was actually run.
- Never weaken or delete a test to make a build pass.
- Never commit secrets or credentials.
- Never push, merge, publish, or deploy without the explicit shipment approval
  gate above — prior approval of a plan is not approval of these.
- Never leave a failure silent — a skipped or disabled check must be named in
  the output, not hidden by a passing exit code.

If a rule here can be made impossible instead of merely stated — a hook that
blocks it, a check that fails the build — prefer that, and remove the rule
from this list once the mechanism exists.

---

## Gotchas

- A hook's failure symptom is silence, identical to "no problem". After
  editing any hook, fire it with `tools/run_hook.py` against a realistic
  payload.
- A skill is invisible if it isn't `<name>/SKILL.md` with a matching `name:`
  in its frontmatter — nothing errors, it just never triggers.
- [project-specific gotcha]

This section should stay short. If it grows past a handful of entries, some of
them likely belong in the tool or script they describe instead of here.

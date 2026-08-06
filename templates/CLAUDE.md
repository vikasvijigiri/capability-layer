# CLAUDE.md

## Project overview

State what this project is, who it's for, and what it optimizes for — two to
three sentences, no more. A reader (human or agent) should know what kind of
work happens here before reading anything else.

Example shape, not content to copy verbatim:
> [Project] is a [kind of system] for [who uses it]. It prioritizes [the one
> or two things that matter most — e.g. reliability, speed of iteration,
> correctness] over [what it explicitly does not optimize for].

If this file is meant to be portable — copied into other repositories rather
than written once for this one — say so here, and keep everything below free
of dates, decision history, and facts specific to a single instance. History
belongs in a changelog or decision log, not in the file loaded every session.

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

Omit anything a linter or config file already enforces without Claude needing
to know it by name.

---

## Commands

The commands run most often, so they don't need to be rediscovered every
session:

    [build command]
    [test command]
    [lint command]
    [dev server / run command]

If there's one command that should run before any work is considered done,
say which one and say so explicitly.

---

## Code style

State conventions that aren't already enforced by a linter — those are the
ones Claude can't infer from tooling and will otherwise guess at.

- Import style: [e.g. named exports only, ES modules not CommonJS]
- File/naming conventions: [e.g. test files live next to source as `*.test.ts`]
- Patterns to follow: [e.g. a standard response shape, an error-handling
  convention]
- Patterns to avoid: [e.g. don't add a new dependency for something the
  standard library already does]

Keep this to conventions that would cause a real problem if violated, not
general best practices Claude already knows.

---

## Project structure

A map of where things live, not a restatement of every file. One line per
top-level concern is usually enough:

| Path | What it is |
|---|---|
| `[path]` | [what lives here and why it's separate] |
| `[path]` | [what lives here and why it's separate] |

If a directory's purpose isn't obvious from its name, that's exactly the kind
of thing this section is for. If it is obvious, leave it out.

---

## Workflow rules

Process the team follows that isn't already enforced by a tool — branch
naming, review expectations, how changes get proposed, anything Claude should
match rather than invent.

- [e.g. open a draft PR before starting non-trivial work]
- [e.g. commits should be scoped to one logical change]
- [e.g. new dependencies need a one-line justification in the PR description]

If any of this is instead enforced by a hook, script, or CI check, say so and
point at it rather than duplicating the rule in prose — a rule stated in two
places drifts when only one gets updated.

---

## Never

The highest-value section: specific, concrete actions that cause real damage
if taken, not general cautions. Each line should be something that, if
violated, costs real recovery time — not a style preference.

- Never [action] — [what it breaks, briefly, if not obvious]
- Never [action]
- Never push, merge, or deploy without explicit approval, unless the project
  has decided otherwise
- Never commit secrets or credentials

If a rule here can be made impossible instead of merely stated — a hook that
blocks it, a check that fails the build — prefer that, and remove the rule
from this list once the mechanism exists. A prevented mistake beats a
documented one.

---

## Gotchas

Non-obvious things that cost someone real time to discover, so nobody else has
to discover them again:

- [e.g. a command that looks safe but has a destructive side effect]
- [e.g. an environment quirk — OS-specific behavior, an env var that must be
  set before a script will run correctly]
- [e.g. a place where a failure is silent rather than an error]

This section should stay short. If it grows past a handful of entries, some of
them likely belong in the tool or script they describe instead of here.
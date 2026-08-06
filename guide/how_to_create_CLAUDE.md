# CLAUDE.md — Template & How to Create It

The one file everything else in this conversation assumes exists.
Skills reference it implicitly, subagents load it at startup (except
Explore/Plan), rules are literally CLAUDE.md content split into modules —
but we never templated the root file itself. Here it is.

## What it is
The always-loaded memory file. Unlike a skill (loads on demand) or a rule
(can be path-scoped), CLAUDE.md loads into **every session, every time**,
at the highest priority. That's exactly why it needs the tightest
discipline of anything in this whole set — every line is a permanent tax
on every session's context, forever.

## Where it lives (load order, broadest → most specific, all loaded together)
| Level | Path | Scope |
|---|---|---|
| Managed/enterprise | admin-deployed | org-wide, can't be excluded |
| User | `~/.claude/CLAUDE.md` | every project on your machine |
| Project | `CLAUDE.md` at repo root | this repo, for everyone (commit it) |
| Nested | `packages/x/CLAUDE.md` | loads lazily when Claude works in that subtree |
| Local | `CLAUDE.local.md` | this repo, gitignored, personal-only |

---

## How to create one

### 1. Start smaller than you think you need
The failure mode isn't an empty CLAUDE.md — it's a 400-line one nobody
reads. Start with the four things a newcomer (human or agent) genuinely
can't infer from the code itself, and add only when you catch yourself
correcting the same mistake twice.

### 2. Write instructions, not documentation
CLAUDE.md is read by an agent about to act, not a person orienting
themselves — that's README's job. Every line should change what Claude
*does*, not just what it *knows*.
```markdown
<!-- Documentation — belongs in README, not here -->
This project uses React with TypeScript and Vite.

<!-- Instruction — belongs here -->
Run `npm run typecheck` before considering any TypeScript change done.
Never use `any` — if a type is genuinely unknown, use `unknown` and narrow it.
```

### 3. Be specific — vague instructions get silently ignored
```markdown
<!-- Weak: "properly" means nothing actionable -->
Write tests properly.

<!-- Strong: checkable, unambiguous -->
Every new function in src/core/ needs a unit test in the matching
tests/core/ file before a PR is opened. Run `npm test -- --coverage`
and don't drop below 80% on touched files.
```

### 4. Structure it so the important parts survive skimming
```markdown
# <Project Name>

## What this is
<1-2 sentences — enough to orient, not a README duplicate>

## Commands
- Build: `<command>`
- Test: `<command>`
- Lint: `<command>`

## Non-negotiables
- <the constraints that must never be violated, stated as facts>

## Conventions
- <patterns specific to this codebase that aren't obvious from reading it>

## Gotchas
- <the thing every new contributor gets wrong once>
```

### 5. Move anything path-specific out to `.claude/rules/`
The moment a section only matters for one part of the codebase (API
routes, one package in a monorepo, frontend styling), it's costing every
session context for work that never touches it. That content belongs in
a scoped rule with `paths:` frontmatter instead — see the rules guide.

### 6. Move anything procedural out to a skill
If a section reads like a runbook — numbered steps, "when the user asks
X, do Y", something with an optional invocation — it belongs in a skill,
which loads on demand instead of every session.

### 7. Don't duplicate AGENTS.md if one exists
If the repo already has an `AGENTS.md` for other tools, don't fork the
instructions into two sources that drift apart — import it:
```markdown
# CLAUDE.md
@AGENTS.md

## Claude Code specifics
Use plan mode for changes under src/billing/.
```

### 8. Keep secrets and personal preferences out of the committed file
Anything environment-specific to you (a sandbox URL, a personal timezone
note, a local-only override) goes in `CLAUDE.local.md`, which is
gitignored — never in the shared, committed `CLAUDE.md`.

### 9. Update it when you catch yourself repeating a correction
The best trigger for a CLAUDE.md edit isn't a scheduled review — it's the
second time you've told Claude the same thing in a session. That's the
signal it should have been standing instruction from the start.

### 10. Verify what's actually loaded
```text
/memory
```
Shows every CLAUDE.md and rules file currently active for the session —
useful after any edit, and essential in a monorepo to confirm you're not
silently pulling in another team's ancestor file.

---

## Template

```markdown
# <Project Name>

## What this is
<1-2 sentences of orientation — not a README duplicate, just enough
context for instructions below to make sense.>

## Commands
- Install: `<command>`
- Dev: `<command>`
- Build: `<command>`
- Test: `<command>`
- Lint/format: `<command>`

## Non-negotiables
- <constraint stated as fact, e.g. "Never commit directly to main">
- <constraint>

## Conventions
- <naming pattern, file organization, testing requirement specific to
  this codebase>
- <anything that would otherwise be reverse-engineered from diff history>

## Architecture notes
<Only what changes how Claude should approach work here — not a full
architecture doc. Link out for anything longer.>

## Gotchas
- <the mistake every new contributor/agent makes once>

## Related
- [README.md](README.md) — full project orientation
- [.claude/rules/](.claude/rules/) — path-scoped conventions
- [HANDOFF.md](HANDOFF.md) — where work currently stands
```

---

## Guardrails
- **~200 lines is the practical ceiling**, not a hard limit — past that,
  every session pays real context cost for content most sessions don't
  need. Treat crossing it as a forced restructure into rules/skills, not
  a reason to trim prose.
- **Don't let this become a README.** If a line doesn't change Claude's
  behavior, it belongs in README instead.
- **Don't let it become a changelog.** "We fixed X on this date" is a
  LOG.md entry, not standing instruction — CLAUDE.md should read the same
  whether it's day one or year three of the project.
- **Launch from the repo root when possible.** Nested/ancestor CLAUDE.md
  loading behavior gets confusing fast in monorepos — `/memory` is how
  you confirm what's actually active rather than assuming.

## Where to verify
`https://code.claude.com/docs/en/memory.md`

---

## What else exists (not yet covered in this conversation)

If any of these would help, ask and I'll build the matching
template+guide:

| Mechanism | What it's for |
|---|---|
| **Plugins** (`.claude-plugin/plugin.json`) | Bundle skills + hooks + agents + MCP servers into one shareable, installable package |
| **MCP server config** (`.mcp.json`) | Connect external tools/data sources (databases, APIs, Slack, etc.) as callable tools |
| **Agent teams** | A lead agent supervising multiple peer sessions that talk to each other — different from subagents, which report back to one caller |
| **settings.json** | The permissions, environment variables, and default modes that govern a whole project or user account |
| **Output styles** | Persistent, swappable response-formatting personas for the whole session |
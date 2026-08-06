# Rules — Templates & How to Create Them

`.claude/rules/*.md` is the mechanism for splitting CLAUDE.md into modular,
often path-scoped files. It's not a new concept — it's CLAUDE.md's content,
organized differently — but it solves a real problem: a single CLAUDE.md
that's grown past a few hundred lines starts costing context on every
session even though most of it is irrelevant to what you're currently
touching.

## Where rules fit versus everything else

| Mechanism | Loads | On what trigger |
|---|---|---|
| **CLAUDE.md** | Always, every session | Session start |
| **Rules** (`.claude/rules/*.md`) | Always, same priority as CLAUDE.md — *or* only when scoped paths match | Session start, or lazily when Claude touches a matching file |
| **Skill** | On demand | Claude decides it's relevant, or you invoke `/name` |
| **Memory** (subagent) | On demand, per-agent | Subagent startup, if `memory:` is set |

The distinguishing test: **is this a standing fact/constraint that should
just be true whenever Claude works in this area**, with no decision to
make about whether to apply it? That's a rule. If it's a *procedure* with
steps, scripts, or optional invocation — that's a skill instead.

---

## How to create one

### 1. Decide: does this even need to be split out of CLAUDE.md?
Don't create rules pre-emptively. The signal is real pain: your CLAUDE.md
has crossed ~200 lines, or it contains sections that only matter for one
part of the codebase (API routes, frontend styling, a specific package in
a monorepo) and loads for everyone regardless.

### 2. Choose scope — global or path-specific
```bash
mkdir -p .claude/rules            # project — always loads, same priority as CLAUDE.md
mkdir -p ~/.claude/rules           # personal — applies across all your projects
```
For monorepos, you can also nest: a rules directory inside a package
applies when Claude works within that package.

### 3. Split by topic, one file per concern
```
.claude/rules/
├── code-style.md        # formatting, naming conventions
├── testing.md            # test requirements, coverage expectations
├── security.md           # security checklist, non-negotiables
└── frontend/
    ├── react.md           # React-specific patterns
    └── styles.md           # CSS conventions
```
This is the actual point of rules over one CLAUDE.md: you can update the
security checklist without touching styling guidance, and a teammate
reviewing a diff to `security.md` immediately knows what changed.

### 4. Add `paths:` frontmatter to scope it (the key feature)
Without `paths:`, a rule loads every session like CLAUDE.md does. With it,
the rule loads lazily — only when Claude actually reads or edits a
matching file — so irrelevant instructions don't sit in context all
session for work that never touches that area.

```yaml
---
paths:
  - "src/routes/api/**/*.ts"
---
API routes must validate input at the boundary and return the shared
error shape. Never return a raw database error to the client.
```

### 5. Write rules as constraints, not procedures
Rules are read passively as context, not executed as steps. Write them
the way you'd write a policy, not a runbook:

```markdown
<!-- Good — a standing constraint -->
All API endpoints must validate input with zod before touching the
database. Errors return `{ error: string, code: string }`, never a raw
stack trace.

<!-- Wrong shape for a rule — this is a procedure, belongs in a skill -->
To add a new endpoint:
1. Create the route file
2. Register it in router.ts
3. Write the validation schema
4. Add tests
```
If you're writing numbered steps, scripts, or "when the user asks for X,
do Y" — that's a skill, not a rule.

### 6. Be specific — vague rules get silently ignored
```markdown
<!-- Weak: Claude interprets "properly" however it wants -->
Format code properly.

<!-- Strong: unambiguous, checkable -->
Run `npm run lint -- --fix` before every commit. Prettier config is in
.prettierrc — do not override it inline.
```

### 7. Share across projects with symlinks, if needed
If several repos should follow the same team conventions, symlink a
shared rules directory into each project instead of copying files that
drift out of sync:
```bash
ln -s ~/shared-conventions/.claude/rules .claude/rules
```

### 8. Exclude rules you don't own, in a monorepo
If launching from a repo root pulls in another team's `.claude/rules/`
you don't want, exclude it privately without touching their files:
```json
// .claude/settings.local.json
{
  "claudeMdExcludes": [
    "packages/other-team/.claude/rules/**"
  ]
}
```
Managed/policy rules can't be excluded this way — they always apply.

### 9. Verify what's actually loaded
```text
/memory
```
Confirms which CLAUDE.md and rules files are active for the current
session — use this after adding a new rule to check it's actually being
picked up, especially for path-scoped ones (which won't show as loaded
until Claude touches a matching file).

---

## Template — global rule (always loads)
```markdown
---
# no `paths:` = loads every session, same priority as CLAUDE.md
---

# <Topic> Rules

- <constraint, stated as a fact, not a suggestion>
- <constraint>
- <non-negotiable, and why it's non-negotiable if not obvious>
```

## Template — path-scoped rule (loads lazily)
```markdown
---
paths:
  - "src/api/**/*.ts"
  - "src/routes/**/*.ts"
---

# API Rules

- All endpoints validate input at the boundary before touching the database.
- Errors return `{ error: string, code: string }` — never a raw stack trace.
- New endpoints require an integration test in `tests/api/`, not just a
  unit test.
```

## Template — team-shared security checklist
```markdown
---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

# Security Checklist

- No secrets or API keys committed, ever — use environment variables.
- User input is validated before it reaches a database query or shell
  command.
- Auth checks happen in middleware, not scattered per-route.
- New dependencies get a quick license/maintenance check before adding.
```

---

## Guardrails before you ship a rules directory

- **Don't use rules for repeatable procedures.** If it has steps, scripts,
  or supporting files — that's a skill. Rules are for standing facts and
  constraints, read passively.
- **Don't skip `paths:` on anything genuinely narrow.** An unscoped rule
  about frontend styling loads on every session including backend-only
  work — that's exactly the context bloat rules exist to solve, recreated
  inside the new mechanism.
- **Don't let CLAUDE.md and rules duplicate each other.** If a fact is in
  both, they'll drift — pick one home. General project orientation stays
  in CLAUDE.md; domain/path-specific detail moves to rules.
- **Don't put personal preferences in project rules.** Team-shared,
  committed rules are for things every contributor should follow.
  Personal-only conventions go in `CLAUDE.local.md` (gitignored) or
  `~/.claude/rules/`.
- **Keep each rule file focused.** One topic per file is what makes the
  "update security without touching styling" benefit real — a rules
  directory with one giant `misc.md` is just CLAUDE.md with extra steps.

## Where to verify
`https://code.claude.com/docs/en/memory.md`
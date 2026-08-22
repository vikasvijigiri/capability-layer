# Creating a Skill — Full Guide

A skill is one file (`SKILL.md`) plus optional supporting files. Unlike a
hook, there's no separate "registration" step — the file's location IS the
registration, and its `description` field is what makes Claude find it.

---

## Step-by-step

### 1. Confirm a skill is actually the right tool
Ask: *is this reusable instructions/knowledge Claude should apply when
relevant, or does it need to happen deterministically no matter what?*
If the latter → you want a hook, not a skill. If unsure, re-check the
primitive-selection table:

| Signal | Use |
|---|---|
| "I keep pasting the same instructions into chat" | Skill |
| "This must always happen, no model judgment" | Hook |
| "This produces output I don't want cluttering my context" | Subagent |
| "This needs 10+ agents and explicit branching/loops" | Workflow |

### 2. Decide who invokes it
This decision shapes two frontmatter fields, so make it before writing
anything:

| Who should trigger it | Set |
|---|---|
| Only Claude, automatically, when relevant | (default — leave both fields off) |
| Only you, explicitly, never automatically | `disable-model-invocation: true` |
| Only Claude, never shown as a `/command` | `user-invocable: false` |
| Both — you can invoke it, Claude can too | (default) |

Rule: **anything with a side effect** (deploy, commit, send a message,
delete something) should be invoke-only. You don't want Claude deciding
*when* to fire something irreversible just because context looked ready.

### 3. Choose the directory (this determines scope)
```bash
mkdir -p .claude/skills/<skill-name>          # project — commit it, team-shared
mkdir -p ~/.claude/skills/<skill-name>          # personal — every project on your machine
```
Precedence when names collide: enterprise > personal > project. A skill at
any level overrides a bundled skill of the same name.

### 4. Write `SKILL.md` — description first, always
The `description` is the *only* thing loaded into context before the skill
is invoked. Everything else in the file is invisible to Claude until it
actually triggers. So:
- Put the primary trigger case **first** in the sentence.
- Use the words a person would actually type, not internal jargon.
- If Claude keeps missing it, the fix is almost always sharpening this
  field — not the body.

```yaml
---
description: Summarizes uncommitted git changes and flags risks. Use when the user asks what changed, wants a commit message, or asks to review their diff.
---
```

### 5. Write the body — what to do, not why
The body loads in full once invoked and **stays in context for the rest of
the session** — every line is a recurring token cost from that point on.
State the procedure as imperative steps. Push anything long (API specs,
example collections) into a separate linked file instead of inlining it.

```markdown
## Instructions
1. <step>
2. <step>
3. <what "done" looks like>

## Additional resources
- Full API details: [reference.md](reference.md)
```

Keep `SKILL.md` short — `templates/Skills.md` states the size rule and why, and
is the one place it lives.

### 6. Decide if it needs live data
If the skill's instructions depend on current state (a diff, a PR, test
output), don't make Claude fetch it — inject it at load time instead:

```markdown
## Current changes
!`git diff HEAD`
```
This runs once, before Claude ever sees the prompt, so the skill arrives
with real data already in it rather than Claude guessing or fetching
separately.

### 7. Decide if it needs isolation
If the skill does real work (not just reference knowledge) — a multi-step
task, something that produces a lot of intermediate noise, something you
want backgroundable — fork it into a subagent:

```yaml
context: fork
agent: Explore        # or general-purpose, Plan, or a custom subagent name
background: true      # false = blocks your turn until it returns
```
Leave `context` unset for a plain reference/knowledge skill — forking only
makes sense when the skill body IS an actionable task.

### 8. Restrict tools if the skill shouldn't need everything
```yaml
allowed-tools: Bash(./scripts/*.sh) Read
disallowed-tools: AskUserQuestion
```
`allowed-tools` pre-approves without a permission prompt, but only for the
turn that invokes the skill — it clears on your next message.

### 9. Test it — invocation AND quality are separate checks
Seeing a skill trigger only tells you Claude *found* it, not that it did
what you wanted. Check both:

```text
What did I change?          # does Claude auto-invoke it?
/summarize-changes           # does the direct invocation work?
```
Then, in a **fresh session** (leftover authoring context masks gaps):
run the same realistic prompts with the skill available, and again with
it disabled (`skillOverrides` set to `"off"`), and compare. If you have
`skill-creator` installed, this comparison is automated:
```text
/plugin install skill-creator@claude-plugins-official
evaluate my summarize-changes skill with skill-creator
```

### 10. Iterate on the description before the body
Claude reads only `name` and `description` to decide whether to trigger a
skill — there is no separate `when_to_use` field in the format. If a skill
fires too rarely: broaden `description` with concrete trigger phrases. If
it fires too often: narrow `description`, or switch to
`disable-model-invocation: true` for full manual control.

---

## Decision cheat sheet

| Question | Field |
|---|---|
| Who can trigger this? | `disable-model-invocation`, `user-invocable` |
| Does it need current live state in the prompt? | `` !`command` `` injection in the body |
| Should it run isolated/backgrounded? | `context: fork` + `agent:` |
| Does it need tools it wouldn't normally get without asking? | `allowed-tools` |
| Should it be barred from certain tools while active? | `disallowed-tools` |
| Does it need a different model/effort just for this? | `model`, `effort` |
| Should it only auto-load in certain files? | `paths` |
| Does it need enforcement that can't be skipped? | pair it with a `hooks:` block |

## Guardrails before you ship one
- **Don't bury the trigger case.** If `description` doesn't lead with the
  thing a user would actually say, auto-invocation quietly fails and you
  won't notice until someone asks why it "isn't working."
- **Don't inline what belongs in a supporting file.** A 500+ line
  `SKILL.md` costs tokens on every invocation for content that's mostly
  unused reference material.
- **Don't skip the fresh-session test.** A skill that "works" in the
  session where you wrote it can still fail for everyone else if the
  description doesn't stand on its own.
- **Don't leave a task-content skill auto-invocable if it has side
  effects.** If in doubt, default to `disable-model-invocation: true` and
  loosen it later, not the other way around.

## Where to verify
`https://code.claude.com/docs/en/skills.md`
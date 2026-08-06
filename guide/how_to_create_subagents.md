# Creating a Subagent — Full Guide

A subagent is one Markdown file with YAML frontmatter. Unlike a skill, its
job isn't to add knowledge to your current conversation — it's to run work
in *complete isolation*, with its own context window, and hand back only a
summary. The whole design exercise is deciding what it should and shouldn't
be able to see or touch.

---

## Step-by-step

### 1. Confirm a subagent is actually the right tool
| Signal | Use instead |
|---|---|
| Reusable instructions applied *inline*, in the current context | Skill |
| Must happen deterministically, no model judgment | Hook |
| Needs dozens of agents with explicit branching/loops | Workflow |
| **A side task would flood your main context with stuff you'll never reference again, OR you keep spawning the same kind of worker with the same instructions** | **Subagent** |

The test that actually matters: *will I need this output later in the
conversation, or just the conclusion drawn from it?* Verbose test output,
log dumps, search results across dozens of files — that's subagent
territory. Something you'll keep referring back to — keep it in the main
conversation.

### 2. Write the description like a routing rule, not a summary
Claude delegates based on this field alone, matched against the current
task. A vague description ("reviews code") competes poorly against Claude
just doing the work itself inline. A description with a concrete trigger
condition gets used:

```yaml
description: Expert code review specialist. Use proactively after writing or modifying code.
```
"Use proactively after X" and "use when Y" phrasing measurably improves
automatic delegation — don't just describe what it does, describe *when*.

### 3. Choose the scope (this decides the directory)
```bash
mkdir -p .claude/agents          # project — commit it, team-shared
mkdir -p ~/.claude/agents         # personal — every project on your machine
```
Ask Claude to write the first draft rather than hand-typing frontmatter:
```text
Create a personal code-improver subagent in ~/.claude/agents/ that scans
files and suggests improvements for readability, performance, and best
practices. Make it read-only and have it use Sonnet.
```
Restart Claude Code once if this is the *first* agent file in a scope that
didn't exist yet — the file watcher only covers directories that existed
when the session started.

### 4. Set `tools` deliberately — this is the main safety decision
Omitting `tools` inherits *everything* the main conversation has access to.
That's rarely what you want. Decide the minimum set the job actually
needs:

```yaml
tools: Read, Grep, Glob, Bash        # read-only reviewer: no Edit, no Write
```
```yaml
tools: Read, Edit, Bash, Grep, Glob  # debugger: needs Edit to actually fix things
```
If it's easier to describe what to *exclude* from an otherwise-full set,
use the inverse instead:
```yaml
disallowedTools: Write, Edit          # keeps everything else, blocks writes
```

### 5. Decide the model — don't default to inheriting without thinking
| Situation | Set |
|---|---|
| No strong reason either way | `inherit` (default) |
| High-volume, mechanical work (search, extraction) | `haiku` — controls cost |
| Genuinely hard reasoning, session usually runs lighter | `opus` or `sonnet` |
| Must stay pinned regardless of what the session switches to | explicit model name |

### 6. Decide the permission mode
Leave `default` unless you have a specific reason to widen or narrow it.
Two things to know before touching this:
- The **parent session's mode can override yours** — if the parent is
  already `bypassPermissions` or `acceptEdits`, that takes precedence
  regardless of what you set here.
- `bypassPermissions` still isn't a total skip — root/home deletions and
  explicit `ask` rules still prompt even in that mode.

### 7. Write the system prompt as a standalone brief
The subagent does **not** inherit your conversation, your CLAUDE.md
philosophy, or the main Claude Code system prompt — only this file's body,
plus CLAUDE.md files and a git status snapshot (unless it's Explore/Plan,
which skip even those). Anything from your main session that must apply
has to be restated here explicitly:

```markdown
You are a senior code reviewer ensuring high standards of quality and security.

When invoked:
1. Run `git diff` to see recent changes
2. Focus only on modified files
3. Begin the review immediately

[checklist, output format...]
```
Be specific about the **output format** you want back — that's the summary
that actually returns to your main conversation, so vague instructions here
produce a vague result there.

### 8. Add memory only if the value compounds over time
```yaml
memory: project
```
This alone does nothing — it just creates the directory. You must also
instruct the agent, in its own prompt, to actually use it:
```markdown
Before starting, check your memory directory for patterns you've seen
before. After finishing, write down anything worth remembering.
```
Use `project` scope by default (shareable via version control); `user` if
the knowledge should follow you across every repo; `local` if it's
project-specific but shouldn't be committed.

### 9. Add isolation only if agents will run in parallel and could collide
```yaml
isolation: worktree
```
Use this specifically when you're spawning several subagents (e.g. a
migration across many files) that each write to the filesystem and must
not step on each other. Skip it for a single read-only reviewer — it's
unnecessary overhead.

### 10. Test both delegation and quality, separately
```text
Use the code-improver agent to suggest improvements in this project
```
confirms Claude *can* delegate to it. But also check whether it delegates
*automatically* on a task that should trigger it, without you naming the
agent — that's the real test of whether the description is doing its job.
If Claude keeps doing the work inline instead of delegating, the fix is
almost always sharpening `description`, not the system prompt.

---

## Decision cheat sheet

| Question | Field |
|---|---|
| What's the minimum this agent needs to touch? | `tools` / `disallowedTools` |
| Does cost or capability matter more than consistency? | `model` |
| Should it operate more/less cautiously than the parent session? | `permissionMode` (parent can still override) |
| Will it accumulate useful knowledge across sessions? | `memory` — but also write the "use your memory" instruction into the prompt itself |
| Will several of these run in parallel touching files? | `isolation: worktree` |
| Should this be reachable by name, explicitly, every time? | invoke with `@agent-name` instead of relying on auto-delegation |
| Should the whole session run as this agent? | `claude --agent <name>` |

## Guardrails before you ship one
- **Don't inherit tools by default.** An unscoped subagent with full tool
  access defeats the purpose — you wanted a bounded worker, not a second
  copy of the main conversation.
- **Don't assume it knows your project conventions.** It doesn't see your
  conversation history or any instructions you gave earlier in the
  session — if a rule matters, it goes in the subagent's own file.
- **Don't set `memory` and assume it's automatic.** Without an explicit
  instruction to read/write it, the directory just sits empty.
- **Don't build a generalist "helper" agent.** One job, one subagent — a
  focused description with a narrow, well-defined trigger gets delegated
  to correctly; a catch-all one competes poorly and gets skipped.
- **Don't forget the parent session can widen your permission mode.**
  `bypassPermissions` or `acceptEdits` upstream overrides whatever you set
  in the subagent file — check what you're actually invoking this from.

## Where to verify
`https://code.claude.com/docs/en/sub-agents.md`
# Creating a Workflow — Full Guide

A workflow is different from the other three primitives in one big way:
you don't usually hand-author it from scratch. You describe the task,
Claude writes the orchestrating script, a runtime executes it in the
background, and you save the result if it's worth repeating. The "creation"
process is really a request-and-refine loop, not a file-writing exercise.

---

## Step-by-step

### 1. Confirm a workflow is actually the right tool
This is the primitive people reach for too early. Check first:

| Signal | Use instead |
|---|---|
| One or two side tasks this turn | Subagent — a workflow is overkill |
| Reusable instructions Claude applies | Skill |
| Needs to happen deterministically, always | Hook |
| **Needs dozens+ agents, explicit branching/loops, or a plan that must survive a context reset** | **Workflow** |

The real signal for a workflow specifically: you want the *orchestration
logic itself* — not just the results — to live outside Claude's context,
because it's too large or too structured for Claude to hold turn-by-turn.

### 2. Decide the shape before you ask
Five shapes cover almost everything. Know which one you're building before
you write the request, because it changes what you tell Claude to do:

| Shape | When |
|---|---|
| **Fan-out + verify** | Same check across many files/items, findings need independent cross-checking |
| **Loop-until-passes** | A checker with a pass/fail signal, fix-and-repeat until clean |
| **Parallel + isolate** | Many independent transforms that must not collide (use `isolation: worktree`) |
| **Review + merge** | Per-item analysis, then one synthesis pass over everything |
| **Search-until-stable** | Open-ended discovery, stop when new rounds add nothing |

### 3. Write the request using the five-line template
```text
use a workflow to <TASK>:
  - discover: <how to find the set of items to process>
  - per item: <what each agent should do to one item>
  - verify: <how findings get cross-checked before being trusted, if at all>
  - combine: <how per-item results become one final answer>
  - stop when: <the termination condition, for open-ended/looping tasks>
```
Fill in only the lines that apply. Or trigger it inline with the keyword
`ultracode` in a normal prompt, or turn on `/effort ultracode` for the
session so Claude plans a workflow for every substantial task without
being asked.

```text
use a workflow to audit every route handler under src/routes/ for missing
auth checks, and adversarially verify each finding before reporting it
```

### 4. Approve the plan
Claude Code shows the planned phases before running. Your options:
- **Yes, run it**
- **Yes, and don't ask again** for this workflow in this project
- **View raw script** — read it before deciding (`Ctrl+G` opens it in your editor)
- **No**

Default and accept-edits modes prompt every run; auto mode prompts once
then remembers; bypass/`-p`/SDK never prompt.

### 5. Test cheap before you commit to expensive
Run it on a narrow slice first — one directory, not the whole repo; one
question, not a broad research task. Watch live cost with:
```text
/workflows
```
This opens the progress view: phases, agent counts, token totals, elapsed
time. A run flagged `Large workflow` (>25 agents or >1.5M projected
tokens) is your cue to stop and reconsider scope before it runs further.

### 6. Read the script if the result looks off
Every run writes its script to disk; ask Claude for the path, or hit
`Ctrl+G` from the approval prompt. It's plain JavaScript — `agent()` spawns
one subagent, `pipeline()` spawns one per item in a list. Read it the same
way you'd read code review feedback: if a stage's prompt is vague, that's
usually why the output is vague.

```javascript
const audits = await pipeline(files, file =>
  agent(`Audit ${file} for missing authentication checks.`, { label: file }),
)
```

### 7. Edit and re-run, or ask Claude to
Two paths:
- Ask Claude directly: *"the verify stage isn't strict enough, tighten it"*
  — Claude edits the script and relaunches.
- Edit the `.js` file yourself, then ask Claude to relaunch from the edited
  version.

### 8. Save it once it does what you want
```text
/workflows → select the run → press s
```
Choose a location:
- `.claude/workflows/` — project, shared, commit it
- `~/.claude/workflows/` — personal, every project, only you

It becomes `/<name>` from then on, and future prompts can pass input:
```text
Run /triage-issues on issues 1024, 1025, and 1030
```
which the script reads as the `args` global.

### 9. Set a size guideline if you'll run this kind of task often
```text
/config → Dynamic workflow size → small | medium | large | unrestricted
```
This is advisory, not a hard cap — Claude can still exceed it if the task
genuinely calls for it — but it steers default sizing so you're not
surprised.

---

## Decision cheat sheet

| Question | Answer determines |
|---|---|
| Does this need to survive a stop/resume? | Design with many small `pipeline()` items, not a few long `agent()` calls — resume only replays what fully finished *before* the first still-running agent at stop time |
| Do results need cross-checking before you trust them? | Add a `verify` stage — a second, independent `agent()` per finding, with no visibility into the first agent's reasoning |
| Will you run this again? | Save it (`/workflows` → `s`) instead of re-describing it each time |
| Will your team run this too? | Save to `.claude/workflows/`, not `~/.claude/workflows/` |
| Is a mid-run decision needed? | Not supported — split into separate saved workflows, one per stage |

## Guardrails before you run one
- **No mid-run human input exists.** If you need a sign-off between
  stages, that's two separate workflows, not one with a pause built in.
- **Concurrency and total caps are real limits, not settings**: 16
  concurrent agents, 1,000 total per run — a workflow that would need more
  needs to be split or scoped down, not configured around.
- **Every agent inherits the session's model unless you route it**
  explicitly — check `/model` before a large run if you'd normally switch
  to something cheaper for routine work.
- **`acceptEdits` is forced on every spawned agent regardless of your
  session's permission mode** — file edits inside a workflow are always
  auto-approved. Don't launch a workflow you haven't reviewed the plan for.

## Where to verify
`https://code.claude.com/docs/en/workflows.md`
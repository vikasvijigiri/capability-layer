# README / HANDOFF / MEMORY / LOG — Templates & What Goes Where

These four solve different problems and get confused constantly because
they all sound like "notes about the project." The fastest way to keep
them from turning into duplicate junk drawers is to know the one question
each one answers:

| File | Answers | Audience | Lifespan |
|---|---|---|---|
| **README.md** | "What is this and how do I use it?" | Anyone arriving fresh — human or agent | Stable — changes only when the project itself changes |
| **HANDOFF.md** | "Where did the last session leave off?" | The next session (you, a teammate, or a fresh Claude instance) | Short-lived — rewritten/cleared each handoff, not accumulated |
| **MEMORY.md** | "What have I learned that isn't obvious from the code?" | A specific recurring agent/subagent, across many sessions | Long-lived, curated — grows slowly, gets pruned |
| **LOG.md** | "What happened, in order?" | Anyone auditing history later | Append-only, grows forever (until archived) |

The test if you're ever unsure which one a fact belongs in: **README** is
timeless truth about the project. **HANDOFF** is "pick up here." **MEMORY**
is a lesson worth not re-learning. **LOG** is a receipt.

---

## 1. README.md

### Content checklist
- [ ] One-paragraph purpose — what this is, in plain language
- [ ] Setup / install steps, copy-pasteable
- [ ] How to run it (dev, test, build)
- [ ] Architecture at a glance — the 5 things a newcomer needs to orient
- [ ] Where to find things — key directories, entry points
- [ ] Conventions that aren't obvious from the code (naming, patterns)
- [ ] Link out to deeper docs instead of inlining them

### Template
```markdown
# <Project Name>

<One paragraph: what this is and why it exists.>

## Setup
\`\`\`bash
<install steps, copy-pasteable, in order>
\`\`\`

## Usage
\`\`\`bash
<the commands someone actually runs day to day>
\`\`\`

## Architecture
<5 sentences max. What talks to what. Link to a deeper doc if it needs more.>

- `src/api/` — <what lives here>
- `src/core/` — <what lives here>
- `scripts/` — <what lives here>

## Conventions
- <naming pattern, testing requirement, anything a contributor would
  otherwise have to reverse-engineer from the diff history>

## Related docs
- [HANDOFF.md](HANDOFF.md) — where work currently stands
- [architecture deep-dive](docs/architecture.md)
```

### What does NOT belong here
- In-progress work, current blockers → HANDOFF.md
- "We tried X and it didn't work because Y" → MEMORY.md
- A record of what changed and when → LOG.md

---

## 2. HANDOFF.md

The single highest-leverage file for agentic work specifically — this is
what lets a new session (fresh context, no memory of the last one) pick up
exactly where things stopped, instead of re-deriving state from the diff
or re-asking you the same questions.

### Content checklist
- [ ] **Current state** — what's actually true right now, in one paragraph
- [ ] **What was just done** — the last completed unit of work
- [ ] **What's in progress** — specifically, not "still working on X"
- [ ] **Next step** — the literal next action, not a vague direction
- [ ] **Blockers / open questions** — anything that needs a human decision
- [ ] **Decisions made and why** — so the next session doesn't re-litigate them
- [ ] **What NOT to do** — dead ends already ruled out

### Template
```markdown
# Handoff — <date/session marker>

## Current state
<One paragraph. If someone read only this, what do they need to know
before touching anything?>

## Just completed
- <specific thing, with file/PR reference if applicable>

## In progress
- <specific thing> — <exact point it's at, e.g. "schema written,
  migration not yet run">

## Next step
<The literal next action. Not "continue implementation" — say what to
actually do first.>

## Blockers / needs a decision
- <question that needs a human, with the options if known>

## Decisions already made (don't re-litigate)
- <decision> — <why, briefly>

## Ruled out
- <approach tried and abandoned> — <why, so it isn't tried again>
```

### The one discipline that makes this actually work
**Rewrite it, don't accumulate it.** A HANDOFF.md that keeps every past
handoff appended becomes a LOG.md with extra steps and stops being useful
— by the time someone needs it, the actually-current state is buried
under history. Overwrite the file each session; if history matters, that's
what LOG.md is for.

### Claude Code specific pattern
Have a `SessionStart` hook cat the file into context automatically, or
just tell Claude at the start of a session: *"read HANDOFF.md before doing
anything."* For a subagent-driven workflow, write the update step directly
into the subagent's or skill's instructions: *"before finishing, update
HANDOFF.md with current state and next step."*

---

## 3. MEMORY.md

This one has a literal, specific meaning in Claude Code: it's the file a
subagent with `memory: project|user|local` set reads and writes
automatically. Claude Code loads the **first 200 lines or 25KB, whichever
comes first**, into that subagent's system prompt at startup — so this
file has a hard size discipline baked into the platform itself, not just
a best practice.

### Content checklist
- [ ] Recurring patterns/conventions the agent has discovered
- [ ] False positives / dead ends — things that looked like issues but
      weren't, so they're not re-flagged every time
- [ ] Architectural decisions and their rationale, as they affect this
      agent's specific job
- [ ] Anything genuinely worth NOT re-learning from scratch each session

### Template
```markdown
# Memory — <agent name>

## Codebase patterns
- <pattern> — <where it shows up, why it's done this way>

## Known false positives
- <thing that looks wrong but is intentional> — <why>

## Architectural decisions relevant to this agent's work
- <decision> — <rationale> — <date/context if useful>

## Open questions / things to verify next time
- <anything uncertain, flagged for follow-up>
```

### The discipline this one requires
Curate ruthlessly — this is knowledge, not a diary. Every session:
1. **Read before working**: instruct the agent explicitly, in its own
   subagent prompt, to check memory first — the field alone doesn't make
   it proactive. `memory: project` just creates the directory; you still
   need "before starting, check your memory" in the system prompt.
2. **Write only what generalizes.** "Fixed bug in auth.ts on line 42" is a
   LOG entry, not a MEMORY entry. "Auth middleware always runs before
   validation, even though the file order suggests otherwise" is a MEMORY
   entry — it changes how future work should be approached.
3. **Prune when it hits the size limit.** Claude Code's own instruction to
   the agent, when the file exceeds 200 lines/25KB, is to curate it down
   — treat that as your own review trigger even if you're maintaining it
   manually: merge duplicate notes, drop anything now obvious from the
   code itself, keep only what still saves real re-discovery time.

### Scope choice
| Scope | Location | Use when |
|---|---|---|
| `project` | `.claude/agent-memory/<agent>/` | knowledge is codebase-specific, shareable via git (recommended default) |
| `user` | `~/.claude/agent-memory/<agent>/` | knowledge should follow you across every repo |
| `local` | `.claude/agent-memory-local/<agent>/` | project-specific but shouldn't be committed |

---

## 4. LOG.md

The receipt file. Boring on purpose — no synthesis, no curation, just what
happened, in order. This is what you'd grep through months later to answer
"when did we decide that" or "what changed right before this broke."

### Content checklist
- [ ] Dated entries, newest either top or bottom — pick one and stay
      consistent
- [ ] One line per event: what happened, not why (that's MEMORY, if it
      generalizes)
- [ ] Links to the actual artifact (commit, PR, session) rather than
      re-describing it

### Template
```markdown
# Log

## 2026-08-05
- Migrated auth middleware to new schema (see #142)
- Added rate limiting to /api/upload
- Session: fixed flaky test in payment flow, root cause was a race
  condition in the mock clock

## 2026-08-04
- Deployed v2.3.1
- Rolled back v2.3.0 due to memory leak in worker pool
```

### The discipline that keeps this useful instead of noise
- **Append-only.** Never edit past entries — if something needs
  correcting, add a new entry that says so, don't rewrite history.
- **Don't let it become a diary.** If an entry needs a paragraph of
  reasoning to make sense, that reasoning belongs in MEMORY.md (if it
  generalizes) or a commit message (if it's specific to that one change) —
  the log entry itself should be one line pointing at the real record.
- **Archive, don't delete, when it gets long.** Roll old entries into a
  dated summary (`LOG-2026-Q1.md`) rather than either keeping one
  ever-growing file or throwing history away — this is the same pattern
  as compacting old MEMORY entries, applied to a different file.

---

## How they work together in practice

A typical session touches all four in this order:

1. **Start**: read HANDOFF.md (where did we leave off) and relevant
   MEMORY.md (what do we already know that isn't in the code).
2. **During work**: nothing gets written yet — these aren't scratch pads.
3. **End of session**: append to LOG.md (what happened), update MEMORY.md
   *only* if something generalizable was learned, rewrite HANDOFF.md with
   the new current state and next step.
4. **README.md** only changes when the project's actual shape changes —
   not every session, not even every week necessarily.

If you're building this into a Claude Code project, the natural place to
enforce the discipline is a `Stop` hook that reminds the agent to update
HANDOFF.md before ending its turn, or a closing instruction in the
relevant skill/subagent prompt — leaving it to memory alone means it gets
skipped under time pressure exactly when it matters most.
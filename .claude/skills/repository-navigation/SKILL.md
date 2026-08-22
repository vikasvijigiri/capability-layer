---
name: repository-navigation
description: Map an unread or half-finished repository before building in it. Entry points, architecture, conventions, what already works and what was left unfinished, plus candidate next steps. Triggers include "what is this repo", "understand this codebase", "walk me through this", "get me up to speed", "onboard me", "I inherited this project", "pick up where this left off", or "where do I even start". Do NOT use for a repository already mapped this session, for a single-file question Grep answers, or to decide what to build (task-analysis). Use this whenever work continues in a repo nobody has read.
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Repository Navigation

Turn an unread repository into a written map and a candidate work list. **Entry
capability, not a lifecycle stage** — it runs before stage 1 when the repo is
unknown, and never runs again once its map exists.

The failure this exists to prevent: the chain starts by framing a *request*. Dropped into a half-built repo, nothing owned the
prior question — *what is this and what stopped halfway*. `tools/resume.py`
could not answer it either; it derives state from this layer's own plan files
and branch names, so a repository that has never used the layer reports
`PLANNING` no matter how much finished work it contains.

## Phase 1 — Measure before reading

Run the deterministic pass first. It is reproducible, costs no judgement, and
tells you where the judgement is worth spending:

```bash
python tools/recon.py
python tools/recon.py --json      # the same facts, if you want to quote them
```

You get: languages and manifests, the test topology, branch and remote state,
recent commits, the most-changed files of the last 90 days, unfinished markers
with `file:line`, and the **disjoint recon units**.

Read three of those numbers before anything else:

| Number | What it decides |
|---|---|
| test ratio near zero | Nothing here can be verified. That is finding #1, not a footnote. |
| uncommitted paths | Someone stopped mid-change. Read that diff before forming any theory. |
| unfinished markers | The previous author's own list of what they knew was missing. |

## Phase 2 — Map the units, in parallel

`tools/recon.py --units` prints subsystems whose file sets are **disjoint by
construction**. That disjointness is the licence to fan out: dispatch one
`researcher` (mode: unit) per unit, **all in a single message**, so they run
concurrently and no two read the same file.

Give each: the unit name, the repo root, and the detected languages. Nothing
more — the brief being small is why this is cheap.

Bound it deliberately:

- **Skip units with no code** unless the question is about docs. `docs/` with 61
  markdown files buys nothing a directory listing did not.
- **Cap the fan-out at the units that matter.** Six mapped subsystems and a named
  remainder beats twelve where you stopped reading at four.
- **Say what you skipped.** A sweep that silently covered half the repo reads as
  one that covered all of it.

When a report comes back, apply the dispatch ladder rather than improvising:

```bash
python tools/loop.py --agent-status NEEDS_CONTEXT --attempt 0
```

`NEEDS_CONTEXT` means supply the one named fact and re-dispatch. `BLOCKED` means
escalate once, then map that unit yourself — never re-dispatch the same brief to
the same model.

## Phase 3 — Write the map

One file, `docs/recon/YYYY-MM-DD-<repo>.md`:

1. **What this repository is** — two sentences, and say if that is a guess.
2. **Stack and how to run it** — the install, test and run commands you found,
   marked *verified* (you ran it) or *inferred* (you read it in a manifest).
   Do not blur the two.
3. **Subsystem map** — one paragraph per unit, from the cartographers' digests.
4. **What is unfinished** — every marker, grouped by subsystem, each with
   `file:line`. This is the section the next stage consumes.
5. **What cannot be verified** — behaviour with no test, and the blast radius of
   changing it blind.
6. **Open questions** — what you could not determine from the repo at all. These
   are for a person; they are not research tasks.

One real excerpt, so the heading text and the verified/inferred labels are
unambiguous rather than assumed:

```markdown
## Stack and how to run it
- Install: `npm install` (verified — ran clean, 0 errors)
- Test: `npm test` (inferred — script exists in `package.json`, not run this pass)

## What is unfinished
- `src/auth/session.ts:42` — marker comment left mid-refactor, token refresh never wired
```

## Phase 4 — Name the candidate work, then stop

From the unfinished list, produce **at most five candidates**, each one line:
what it is, where it lives, and why it looks unfinished rather than deliberate.

Then stop. You do not choose. A repository full of `TODO`s is not a backlog —
half of them were decisions, and only the owner knows which half.

## Constraints

- **Never infer intent from absence.** A missing feature is not a planned one.
  Say "not present" and let the next stage decide whether it should be.
- **Never run install, build, migrate or deploy commands to find out what they
  do.** Read them. A recon pass that mutates the repository it is describing has
  changed the thing under measurement.
- **Verified and inferred are different words** and the difference is whether you
  ran it. Every command in the map carries one of the two labels.
- **Do not repair what you find.** A recon that fixes three things has an
  unreviewed diff and no map. `debugging` owns a real failure;
  `refactoring` owns cleanup.
- **Cap the map at what a person will read.** If it passes ~400 lines, the
  per-unit detail belongs in the cartographers' digests, cited by path.

## Red flags — you are guessing, not reconnoitring

- "This looks like a standard Express app, so it probably…" — read the routes.
- "The tests presumably cover the happy path." — run them, or say you did not.
- "I'll fix this TODO while I'm here."
- Summarising a subsystem no cartographer read and you did not open.
- A map with no `## Open questions` section. Every unfamiliar repo has some.

## Success

A map exists at `docs/recon/`, every command in it is labelled *verified* or
*inferred*, every unfinished item carries `file:line`, the untestable surface is
named rather than omitted, and someone who has never opened this repository could
pick the next piece of work from the candidate list without reading code first.

## Routing

- **Entered from**: a session opening in a repository nobody has read, or
  `.claude/install.py` reporting an existing codebase with no plan.
- Ambiguity in *what the repo does* is answered here. Ambiguity in *what to
  build* is not — that is the next stage's.
- Needs outside evidence about an unfamiliar framework or protocol? `research`.
- Found something actually broken rather than merely unfinished?
  `debugging`, with the `file:line` from the map.
- The map itself is durable knowledge: `documentation` owns filing it
  alongside `HANDOFF.md` once a unit of work begins.
- **Terminal handoff**: the chain's entry, which `.claude/workflow.md` §Entry
  owns — one door, `task-analysis`. See **Next step** for why recon does not
  decide what happens behind it.

## Next step — you MUST take it

**The terminal state is invoking `task-analysis`** with the map written and the
candidates listed. Recon that ends in a summary and no brief has produced
reading, not work. If the direction the repo should go is genuinely open rather
than merely unstated, `task-analysis` dispatches `architecture` itself before it
frames anything — that is its decision, not this skill's.

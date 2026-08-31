---
name: implementation
description: Carry out an approved plan test-first in an isolated worktree. Writes the failing test before the code and ticks each task only when its own check passes. Triggers include "execute the plan", "implement this", "start building", "do task 3", "next task", "continue the plan", "write a failing test first", "create a worktree", or "keep this off main". Do NOT use to write the plan (task-analysis), to diagnose a failure (debugging), or to judge whether the result meets the brief (testing). Use this whenever an approved plan is about to be built.
effort: medium
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Implementation

Carry out an approved plan and produce the thing it describes. Runs after
approval and before verification — not instead of either.

Implementation starts only in an isolated line of work: follow the project's
convention if it has one, otherwise create a dedicated branch before task 1 and
record its name and base commit.

Cap visible output at ~500 tokens. One line per task boundary; the plan file and
the tool results carry the record.

<HARD-GATE>
NEVER tick a step, or say a task is done, on a verification you did not run and
cannot quote.

Exit 0 is not proof the effect occurred. Read the result back: query the setting
you changed, count the rows, call the tool you registered, fire the hook you
edited. The recurring failure in agent-written work is *prose declaring a
capability the wiring does not implement*, and every instance was a step marked
complete on a command that returned successfully.
</HARD-GATE>

## Before Task 1: read the plan and argue with it

Read it once, then scan for what would break execution:

- tasks that contradict each other or the plan's Constraints
- a task depending on something no earlier task produces
- a step whose verification cannot fail — it proves nothing
- anything the plan mandates that a reviewer would call a defect

Present everything **as one batched question**, each finding beside the plan text
that mandates it. One interrupt before execution, not one per discovery. If the
scan is clean, say nothing and start.

Planning self-reviews for this class, but that happens before approval — the plan
may have been edited since, and you are the last reader before it becomes real.

## The progress record is the plan file

Tick `- [ ]` → `- [x]` as each step lands. **Do not create a ledger file.** The
need is real — context resets lose your place — but the plan file and version
control are already durable state. After a reset, trust the plan's checkboxes and
the commit history over your own recollection.

## The task loop

Per task, in order:

1. Read the task's **Files**, **Implementation notes** and **Verification**
   before touching anything. The plan already names the symbols and the command.
2. Write the failing test first when the task changes behaviour — see
   `references/test-driven-development.md`.
3. Make the change, limited to the files the task names. A file the plan did not
   name is scope escape, not initiative.
4. Run the task's own **Run:** command and compare against its **Expect:**.
5. Tick the checkbox, report **one line**, move on.

Do not pause for approval between tasks — a task in a well-formed plan ends with
an independently testable deliverable, which is where the seam belongs.
Mid-task check-ins have no artefact to show.

Four things stop the loop:

| Stop | Do |
|---|---|
| A verification fails, or fails repeatedly | Start debugging deliberately. Not guessing, not asking |
| The plan is wrong, or silent where it matters | Ask, with the plan text beside the problem |
| You deviated from the plan | Reconcile — see below |
| The next step pushes, merges, publishes or deploys | Stop and get explicit approval in the conversation |

**Verify with the cheapest tier that answers the question.** A task's own check
is its named command; when a whole-tree check is needed mid-run, that is
`python tools/run_checks.py --scoped`. The full tier belongs to the last
verification before delivery, not to every task boundary.

## Deviation must be reconciled, never left implicit

If implementation diverges from the plan — a better structure, a constraint the
plan missed, a local convention that contradicts it — either **amend the plan
file with the reason** or **revert to the plan**.

Never leave an unreconciled divergence for the reviewer to find. A convention
comment in one file is a claim about a local choice, not evidence of a global
rule; grep for counter-examples before letting it override the plan.

## Committing costs a review

A plan whose every task ends in "commit" needs a review sign-off per task,
because each commit delivers content nobody has looked at. Say which you are
doing **before Task 1**:

1. **Commit per task** — sign off each through review. Clean history.
2. **Execute the run, commit once** — one review over the whole change.

Nothing enforces this choice, so decide and say it up front, or batching becomes
the default without anyone deciding it.

## Open-ended work: the loop mode

For work with no fixed task list, the plan is a direction and the shape is two
loops:

- **Inner loop:** pick the highest-priority untested hypothesis → write the
  protocol and what it predicts → **commit the protocol before running it** →
  run → sanity-check before trusting the number → record the outcome.
- **Outer loop**, every 5–10 inner passes or when a pattern appears: review the
  results together, ask *why*, update the findings document, then decide
  **DEEPEN**, **BROADEN**, **PIVOT**, or **CONCLUDE**.

Locking the protocol before the run separates confirmatory from exploratory:
version-control history proves the plan predated the result. A refuted hypothesis
is progress — record what it rules out.

State the termination criterion before starting. A loop without one does not
terminate.

## Dispatching subagents for parallel tasks

**Concurrent dispatch is the default, not an ask.** Run `python
tools/parallel_groups.py <plan>` before Task 1 of any plan with more than one
task. Any round it reports with concurrency > 1 is dispatched concurrently
without waiting for the user to request it — the scheduler's own proof of
disjoint file sets and frozen interfaces is the license. A non-zero exit means
the plan is not schedulable; fix the plan (or run it serially), never route
around the check.

**Each task in such a round gets its own branch, not a shared scratch
worktree.** Create it yourself — never rely on `implementer`'s own
`isolation: worktree` frontmatter (see `references/parallel-dispatch.md`'s
"own the worktree instead of asking for one"):

    python tools/worktree.py create <task-name> <plan-base-branch> \
        --branch <slug>/task-<N>

`<plan-base-branch>` is this plan's own working branch tip, verified by `git
merge-base --is-ancestor` — never the repository's default branch; that
mistake is the one prior fan-out failure this layer has on record. Dispatch
one agent per task in the round, all in the same message, each pointed at
its pre-created worktree path: **`backend-engineer`** when the task's
declared `Files:` are backend paths (a server/api/backend/service
directory, or a backend language/framework file), **`frontend-engineer`**
when they are frontend paths (a client/frontend/ui/components directory, or
a `.tsx`/`.jsx`/`.vue` file), otherwise the generic **`implementer`**. The
choice is read from the task's own file set before sending the round's
message — `tools/parallel_groups.py` still only proves disjointness and
rounds, not which agent to send.

Give each agent: the **path** to its task's text (never pasted — anything
pasted stays in your context for the session), the interfaces earlier rounds
produced, the plan's constraints, and where to report back.

Read what each agent reports rather than trusting it succeeded. Resolve every
non-clean result deliberately — a blocked agent gets escalated or reassigned
once, never re-dispatched unchanged. Verify the round before dispatching the
next: an agent reporting success is not evidence; the diff is.

**The dispatcher — never the subagent — commits.** `implementer`'s own
contract already forbids it ("Never commit, push, merge or deploy"). Once a
task's diff and its own Verification command both check out, commit it
yourself inside that task's worktree, on that task's named branch. Hand the
resulting list of committed branches to `release-git`, which pushes and opens
one PR per branch automatically and gates the eventual merge behind one
batched confirmation covering the whole round — see `release-git/SKILL.md`'s
"Exception: a parallel round's task branches". Do not merge these branches
into the plan's own working branch yourself; that is what `release-git`'s
batched step is for.

Read `references/parallel-dispatch.md` before the first fan-out.

## Environment gotchas that bite during execution

- **Toolchain and locale mismatches surface as fake failures.** A script printing
  non-ASCII can raise an encoding error on a default console — that looks like
  the change failed, not like an environment mismatch.
- **A misconfigured hook or scheduled job fails silently** — its symptom is
  indistinguishable from "no problem". After editing one, trigger it directly
  against a realistic input.

## Red Flags — you are not executing, you are improvising

- "The command exited 0, so it worked."
- "I'll note the deviation in the summary at the end."
- "This step's verification is obvious, I'll skip running it."
- "The plan says commit here but I'll batch it and mention it later."
- "I'll fix the failing test myself, quickly." That's a debugging problem.
- "They'd obviously approve this push."
- Ticking a checkbox for a step you did not run.

**Each of these means: stop, run the thing, and quote what it printed.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Pausing between every task for approval | The plan was the approval |
| Creating a progress ledger file | Another owner of state; the checkboxes already are one |
| Guessing at a failing verification | The failure should trigger dedicated debugging |
| Deviating silently | The reviewer finds it instead, and the round is wasted |
| Pasting task text into a subagent prompt | Resident in your context for the rest of the session |
| Running an open-ended loop with no termination criterion | It does not terminate |

## Techniques — read one when the task calls for it

| The task involves | Read |
|---|---|
| new or changed behaviour needing executable proof | `references/test-driven-development.md` |
| multi-file, parallel or risky work that must not touch the checkout | `references/using-git-worktrees.md` |
| more than one agent to dispatch, or one that came back blocked | `references/parallel-dispatch.md` |

Isolation is decided **before** the first edit, not after the diff grows.

## Next step — you MUST take it

**The terminal state is invoking `testing`**, once every task is ticked.
Every task green is not the same as the goal met, and this skill cannot judge its
own output. Do not announce completion before verification has run.

Before that handoff, dispatch `reviewer` (mode: spec) when the implementation has an
approved spec or material acceptance criteria — it checks compliance but does not
fix or approve the work. Scope its prompt to plan-vs-diff compliance only: does
every task's Files/Implementation notes/Done-when match what actually landed.
Re-running the test suites is `testing`'s `tester`, dispatched
next — asking both agents to do that is the same suite run twice.

## Routing

- Mandatory validator: verification of the completed work.
- Independent compliance lens: `reviewer` (mode: spec) for material approved specs.
- Preceded by planning, which produces the plan this consumes.
- Terminal handoff: `testing`, then `release-git`.
- A failure worth remembering goes wherever the project tracks issues; the unit
  goes wherever it records history.
- Before anything irreversible, stop and ask in the conversation.
- Consult `engineering-standards` before writing backend or frontend code,
  for current industry-practice grounding.

## Success

The plan's checkboxes are ticked only where a verification was run and quoted,
every deviation is written into the plan file with its reason, and the reason
each stop happened is visible — not discovered later by a reviewer.

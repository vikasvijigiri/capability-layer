---
name: writing-plans
description: Turn an approved spec into ordered, verifiable tasks. Triggers include "write the implementation plan", "turn the spec into tasks", "break this down", "review the plan", "does this cover everything", "what order should we build this in". Do NOT use before a spec exists (brainstormer), for a small scoped brief (task-brief), or to implement it (executing-plans). Use this whenever a spec is ready to become tasks.
when_to_use: when an approved spec must be turned into executable tasks
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob Task
---

# Writing Plans

Create a detailed implementation plan from an approved specification. The
deliverable is a plan document, not production code, scaffolding, migrations,
tests, or implementation edits.

## Hard boundary

- Read and inspect the repository; do not modify source, tests, configuration,
  or documentation other than the plan being created.
- Do not execute the plan while writing it. Do not invoke `executing-plans`,
  implement a task, or claim that the feature is built.
- Do not invent requirements. **Never guess.** Write
  `[NEEDS CLARIFICATION: <the exact question>]` inline where the answer belongs
  and keep going — a marker costs one line, a wrong assumption costs the build.
  Return to `brainstormer` only if the approach itself is unsettled.
- Do not start without an approved spec. A rough request belongs to
  `task-brief`; an unsettled direction belongs to `brainstormer`.

## Procedure

### 1. Confirm the input

Announce: "I'm using the writing-plans skill to create the implementation plan."

Read the approved spec completely. Extract the goal, non-goals, constraints,
acceptance criteria, affected user flows, and explicit technical decisions.
Confirm that the spec describes one coherent deliverable. If it spans
independent subsystems that could be built and verified separately, stop and
recommend separate specs and plans.

For a material feature or architectural change, apply
`references/artifact-review.md` to the
spec before drafting the plan. A REVISE verdict returns to `brainstormer`; do
not plan around an independently identified spec gap.

For cross-cutting boundaries, dispatch `architecture-reviewer`; it reports risks
while this skill owns the plan and the approval gate.

### 2. Inspect the repository before designing tasks

Inspect the current branch and working tree. Locate the existing implementation,
tests, configuration, build commands, conventions, and neighboring features.
Read the relevant files end-to-end where practical; do not plan from filenames
or from the spec alone.

Record the evidence that determines the plan:

- existing files and their responsibilities;
- extension points, interfaces, data flow, and dependencies;
- test seams and the commands that exercise them;
- generated files or migration rules that must not be edited directly;
- repository constraints, platform assumptions, and known risks.

### 3. Freeze the file map

Before defining tasks, write a file map. For every file the implementation may
touch, state whether it will be created, modified, moved, or deleted and what
responsibility it owns after the change. Prefer focused changes that follow the
repository's existing structure. Do not propose a refactor merely because a
different layout would be cleaner.

Every planned file must have a reason. Every requirement in the spec must map
to at least one file or to an explicit verification step.

### 4. Decompose into executable tasks

Order tasks by dependency, from foundations to behavior to integration and
documentation. A task is the smallest independently reviewable change that
has its own verification cycle; split tasks when a reviewer could accept one
part and reject another.

Each task MUST include:

```markdown
### Task N: [Component or behavior]

**Purpose:** [the observable outcome]

**Files:**
- Create: `exact/path` — [responsibility]
- Modify: `exact/path:relevant-symbol` — [change]
- Test: `exact/path` — [coverage]

**Dependencies:** [earlier task BY NUMBER, or `none` — never prose, never blank]

**Implementation notes:**
- [exact symbols, data flow, invariants, and edge cases]
- [interfaces consumed and produced, including names and types where known]

**Verification:**
- Run: `[exact test or check command]`
- Expect: [observable passing result]

**Done when:** [a concrete, reviewable condition]
```

**`Files:` and `Dependencies:` are machine-read, so write them for a parser as
well as a reader.** `tools/parallel_groups.py` turns them into the rounds
`executing-plans` dispatches, and it refuses a plan rather than guessing:

```bash
python tools/parallel_groups.py <this plan>
```

Run it before presenting the plan at Gate 1. Three rules it enforces, each of
which is a real defect it has caught in a plan written here:

- **Every path the task writes appears under `Files:`.** An undeclared path is
  one the scheduler cannot see, and two tasks colliding on it look disjoint.
- **`Dependencies:` is a task number or the word `none`.** Never blank, and never
  prose — "the store's read API" is a real dependency this cannot resolve, and
  reading it as independence dispatches ordered work concurrently.
- **A task touching a migration, lockfile or CI config gets its own round**
  automatically. You do not have to sequence those by hand; you do have to
  declare them.

A plan that is entirely serial is a fine answer. A plan that *reports* as
entirely parallel because its dependencies were left implicit is not.

Use test-first sequencing for behavior that can be tested: define the failing
case, identify the minimal implementation required, then define the passing
check. Include production-code sketches only when they clarify an interface;
do not write complete implementation bodies into the plan.

Do not use vague steps such as "implement appropriately", "add validation",
"handle edge cases", "write tests", or "finish the remaining work". Replace
each with the exact file, symbol, behavior, test input, expected result, and
command an implementer needs.

Do not include a task for committing, pushing, merging, or deploying. Those are
controlled by the execution, review, delivery, and release stages. Mention a
safe checkpoint only when it is a repository convention the executor must
observe.

### 5. Write the plan document

Save the plan at:

`docs/plans/YYYY-MM-DD-<feature-name>.md`

Use a stable, descriptive feature name. The document MUST begin with:

```markdown
# [Feature Name] Implementation Plan

**Goal:** [one sentence]

**Source spec:** [path to the approved spec]

**Slug:** [the unit of work, matching the branch — see below]

**Architecture:** [the chosen approach and why it fits the existing system]

**Tech stack and constraints:** [versions, boundaries, conventions, and non-goals]

## File map
...

## Tasks
...
```

**`**Slug:**` is machine-read and is not decoration.** `tools/resume.py` keys
every derived fact off one slug — the plan, `refs/uaios/green/<slug>`, the attempt
ledger — and it took the slug from the FILENAME until 2026-08-08. A plan named
after its feature while the branch is named after something else therefore matched
nothing, and the engine reported the unit as having no plan at all: the same
answer a fresh repository gives. Declare the slug and the filename is free to say
what the plan is about.

Keep the plan self-contained. An engineer who has not participated in the
conversation should be able to execute each task without guessing what a path,
symbol, test, or dependency means.

### Constitution gate — tick or justify

Every plan carries this block. An unticked box is legal; an unticked box with no
written reason is not. `.claude/constitution.md` holds the articles.

```markdown
## Constitution gate
- [ ] I Evidence — every task names the exact command and the expected output
- [ ] II Test first — every behaviour task defines its failing test first
- [ ] III Smallest change — no refactor beyond what the task requires
- [ ] IV Reversibility — irreversible steps are named and gated on a human
- [ ] V No silent degradation — checks that will be skipped are listed here
- [ ] VI Mechanism — any rule this plan adds is enforced by a test or a hook
- [ ] VII Secrets — no credential enters the repo

## Complexity tracking
<one line per unticked box: which article, and why the exception is right>
```

### The two markers the machinery reads

`tools/resume.py` derives the workflow state from this file, so these two strings
are contract, not style:

| Marker | Meaning |
|---|---|
| `[NEEDS CLARIFICATION: q]` | an open question, inline where the answer belongs |
| `## Approved` | the user passed Gate 1 |

**A marker outranks approval.** While any remains, the derived state is
`WAITING_PLAN_APPROVAL` no matter what else the file says — so a plan cannot be
approved over an open question, and the enforcement is a function rather than a
reviewer's attention.

### 6. Self-review before handoff

First run the mechanical pass — it is cheap and it finds what reading misses:

```
python tools/analyze.py --slug <slug>
```

It reports missing sections, unresolved markers, unjustified gate exceptions,
tasks with no verification command, and `Modify` targets that do not exist. Fix
every finding before spending a review on the plan.

Then apply `references/artifact-review.md` to the completed plan. Treat its verdict as
independent evidence; do not silently repair a rejected plan in the same pass.

Then review the completed plan against the spec, not against memory:

1. Coverage — every requirement, acceptance criterion, and constraint has a
   task or verification step.
2. Ordering — no task consumes a file, symbol, schema, or interface that a
   later task creates.
3. File accuracy — every path exists or is explicitly marked for creation;
   symbols and neighboring patterns match the repository.
4. Testability — every behavior-changing task has a concrete test or check,
   with expected output and failure coverage where practical.
5. Completeness — no placeholders, hidden decisions, accidental scope, or
   production implementation disguised as plan prose.
6. Execution safety — irreversible actions, migrations, credentials, and
   external integrations have explicit constraints and rollback considerations.

Fix gaps in the plan before presenting it. If a gap reveals that the spec is
incomplete or the approach is unsettled, stop and route back to the appropriate
earlier skill instead of filling the gap by assumption.

## Independent artifact review

The artifact-review skill was separate; it is now
`references/artifact-review.md`. Read it when the spec or plan is material enough
that an independent verdict is worth the pass — a cross-cutting change, a new
boundary, anything hard to reverse. For architectural risk, dispatch
`architecture-reviewer`; it reports, this skill still owns the plan and the gate.

## Completion and handoff

The skill is complete only when the plan is saved, self-reviewed, and presented
for the plan approval gate. State the plan path, task count, key assumptions and
known risks.

<!-- GATE 1: plan approval. The chain has two; see .claude/workflow.md. -->
**Then put every `[NEEDS CLARIFICATION]` marker into one `AskUserQuestion` call.**
One batch, at the gate — not a question each time one arises. Scattered questions
are what turned two gates into nine, and they interrupt at the moment the answer
is least informed.

The same call carries the approval, with three real options:

| Option | Means |
|---|---|
| Approve | write `## Approved`, hand off to `executing-plans` |
| Revise — say what to change | rejected, and the free text is the brief |
| Reject — wrong approach | the plan is not the problem; return to `brainstormer` |

**The revise and reject options take the user's own words.** Say so in the
question. The tool appends its own "Other" for free text — never add one — and
whatever comes back, including anything in the answer's notes, is recorded
verbatim. A reason paraphrased is a reason lost.

On anything but approve, append to the plan and stop:

```markdown
## Rejected <date> (plan <8-char body hash>)
<the user's words, verbatim>
```

`tools/resume.py` reads that log. Re-presenting a plan whose body hash is
unchanged is refused — asking again about an artifact the user already judged
spends their attention on a question they have answered. Three rejections and
`tools/loop.py` says retreat: a fourth draft of a plan nobody wants is not
convergence, and the objection was never about the wording.

After the user approves the plan, invoke `executing-plans` and pass it the plan
path. Until approval is explicit, stop here.

## Next step — you MUST take it

The terminal state is invoking `executing-plans` after the user approves the
saved plan. Pass the plan path. Do not implement any task in this skill.

## Routing

- Mandatory validator: the self-review in this skill; no implementation suite
  runs because this skill produces a plan, not product code.
- Independent validator: `references/artifact-review.md` for material specs and plans.
- Preceded by `brainstormer`, which produces the approved spec consumed here.
- Terminal handoff: `executing-plans`, only after the plan approval gate.
- If the spec is incomplete or the approach is unsettled, return to
  `brainstormer`; do not fill the gap by assumption.

## Success criteria

- A dated plan exists under `docs/plans/`, named `<date>-<slug>.md` where `<slug>`
  matches the branch (`feat/<slug>`) — one slug ties plan, branch, green ref and PR.
- The plan describes implementation work without performing it.
- Tasks are ordered, independently verifiable, and specific enough to execute.
- Every open question was a marker, and every marker was answered at the gate —
  none invented, none left behind.
- Every spec requirement and affected file is accounted for.
- Execution has not started before approval.

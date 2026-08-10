# The plan document

How to write the file `writing-plans` Stage C produces: its required header,
the two strings the machinery parses out of it, the constitution gate, and
the self-review that runs before Gate 1.

Split out of `SKILL.md` because the skill exceeded its 200-line prose budget
after absorbing the framing stage -- `tools/test_no_slop.py --scope layer`
calls that a god-skill smell, and it was right that this is the separable
half. Read it when writing the plan; the skill body carries the decisions.

---

### C5. Write the plan document

Save the plan at:

`docs/plans/YYYY-MM-DD-<feature-name>.md`

Use a stable, descriptive feature name. The document MUST begin with:

```markdown
# [Feature Name] Implementation Plan

**Goal:** [one sentence]

**Source brief:** `TASK.md`, plus any spec under `docs/specs/`

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
ledger — and it once took the slug from the FILENAME. A plan named
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

### C6. Self-review before handoff

First run the mechanical pass — it is cheap and it finds what reading misses:

```
python tools/analyze.py --slug <slug>
```

It reports missing sections, unresolved markers, unjustified gate exceptions,
tasks with no verification command, and `Modify` targets that do not exist. Fix
every finding before spending a review on the plan.

Then apply `references/artifact-review.md` to the completed plan. Treat its verdict as
independent evidence; do not silently repair a rejected plan in the same pass.

Then review the completed plan against the brief, not against memory:

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

Fix gaps in the plan before presenting it. If a gap reveals that the approach is
unsettled, return to Stage B and dispatch rather than filling it by assumption.

---

## Recording a rejection

The gate's revise and reject options carry the user's own words. The tool appends
its own "Other" for free text — never add one — and whatever comes back,
including anything in the answer's notes, is recorded verbatim.

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

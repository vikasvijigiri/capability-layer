# Decomposing a plan into tasks

The required shape of a task block, and the three rules
`tools/parallel_groups.py` enforces on the `Files:` and `Dependencies:`
fields it parses out of them.

Split out of `SKILL.md` under the same 200-line prose budget that moved
`plan-document.md`. This is the template half; the skill body keeps the
decisions about ordering and granularity.

---

### C4. Decompose into executable tasks

Order tasks by dependency, from foundations to behavior to integration and
documentation. A task is the smallest independently reviewable change that
has its own verification cycle; split tasks when a reviewer could accept one
part and reject another.

## The `## Progress` block — emit it, or the executor has nothing to tick

Every plan carries one, directly above `## Tasks`, with **one checkbox per
task**:

```markdown
## Progress

Ticked by `executing-plans` as each task's own **Verification** command is run
and quoted. Nothing here is ticked on a clean diff or a zero exit code.

- [ ] Task 1 — <title>
- [ ] Task 2 — <title>
```

**This block did not exist until a plan needed it and had none.**
`executing-plans` says *"Tick `- [ ] → - [x]` as each step lands. `writing-plans`
mandates that syntax expressly for tracking"* — and it did not. The task template
below emits `**Done when:**` and no checkbox, so across every plan in
`docs/plans/` there were zero task checkboxes and the executor's entire progress
mechanism had never once had anything to tick.

`tools/analyze.py` now counts the boxes against the `### Task N` headings and
reports a mismatch, so a plan that adds a task without adding its box is a
finding rather than a silent drift.

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

**Rollback:** [one line: how to undo this task's change if it must come out]

**Preconditions:** [one line: what must still be true before starting this task]

**Verification:**
- Run: `[exact test or check command]`
- Expect: [observable passing result]

**Done when:** [a concrete, reviewable condition]
```

**`Rollback:` and `Preconditions:` are per task, not per plan** — `tools/analyze.py`
checks each task's own body, so a rollback line stated once for the whole plan
does not cover the tasks after it. Keep both to one line: a field nobody can
fill in a sentence becomes boilerplate, and boilerplate is worse than an absent
field because it reads as considered when it was not. A plan written before
these fields existed states its exemption once, by name, under `## Complexity
tracking` — `analyze.py` only recognizes an exemption that names both fields;
a bare "predates this" is not enough, or every later plan's silence would read
as the same exemption.

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

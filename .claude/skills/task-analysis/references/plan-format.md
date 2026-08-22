# Plan document format — the exact templates

Split out of `task-analysis/SKILL.md`'s Stage C, a compression pass, so the
main body states the procedure once and points here for the literal shape
to copy. Read this at C3/C4, not before.

## The Progress block (C3)

Every plan carries a `## Progress` block directly above `## Tasks`, one
checkbox per task. `implementation` ticks it as each task's own
**Verification** command runs and is quoted — never on a clean diff alone:

```markdown
## Progress
- [ ] Task 1 — <title>
- [ ] Task 2 — <title>
```

## A filled task instance (C3)

One filled instance, so the shape is unambiguous rather than assumed:

```markdown
### Task 2: Encrypt UserProfile.birth_datetime at rest
**Purpose:** the field is unreadable in a raw DB dump
**Files:**
- Create: `lib/encrypted_string.py` — SQLAlchemy type wrapping AES-GCM
- Modify: `models/user_profile.py:birth_datetime` — use the new type
- Test: `tests/test_encrypted_string.py` — roundtrip and migration
**Dependencies:** 1 (key loading must exist first)
**Implementation notes:** key from env `APP_DB_KEY`; nonce per row, stored
alongside ciphertext, never reused
**Rollback:** revert the migration; column reverts to plaintext
**Preconditions:** `APP_DB_KEY` set in every target environment
**Verification:**
- Run: `pytest tests/test_encrypted_string.py`
- Expect: roundtrip passes; the raw column value is not human-readable
**Done when:** `alembic upgrade`/`downgrade` is clean on an empty DB and no
plaintext value remains in the table after migration
```

Every task template, for reference:

```markdown
### Task N: [Component or behavior]
**Purpose:** [the observable outcome]
**Files:**
- Create: `exact/path` — [responsibility]
- Modify: `exact/path:symbol` — [change]
- Test: `exact/path` — [coverage]
**Dependencies:** [earlier task BY NUMBER, or `none` — never prose, never blank]
**Implementation notes:** [exact symbols, data flow, invariants, edge cases]
**Rollback:** [one line: how to undo this task's own change]
**Preconditions:** [one line: what must already be true before starting]
**Verification:**
- Run: `[exact test or check command]`
- Expect: [observable passing result]
**Done when:** [a concrete, reviewable condition]
```

`Files:` and `Dependencies:` are machine-read, so write them for a parser
as well as a reader — one bullet per file, full path every time, never a
comma-joined list or an inherited prefix from an earlier bullet
(`tools/analyze.py`'s `FILE_RE` and `tools/parallel_groups.py` both require
the exact `- Verb: \`path\`` shape).

## The plan document header (C4)

Write the plan document at `docs/plans/YYYY-MM-DD-<feature-name>.md`,
beginning:

```markdown
# [Feature Name] Implementation Plan

**Goal:** [one sentence]

**Source brief:** `TASK.md`, plus any spec under `docs/specs/`

**Slug:** [the unit of work, matching the branch]

**Risk:** [computed, never judged -- run `python tools/scope.py --plan <this
file>` and paste its one-line reason. A shared or control surface forces
high; volume or spread forces medium; a sensitive surface (auth, credentials,
installer, packaging, CI) forces high on its own; an unclassifiable plan is
high, never low. Not permission to skip Gate 2.]

**Blast radius:** [surfaces, consumers, data this change can reach]

**Rollback:** [how to undo THIS PLAN at its worst landing state -- half the
tasks merged, already delivered -- and what's left behind if the undo isn't
clean]

**Architecture:** [the chosen approach and why it fits the existing system]

**Tech stack and constraints:** [versions, boundaries, conventions, non-goals]

## File map
...
## Progress
...
## Tasks
...
```

**A blank line separates every field above.** Markdown collapses
consecutive lines with no blank line between them into one run-together
paragraph — eight fields written that way render as a single dense block
nobody can scan. One blank line per field is the whole fix, and it is not
optional: a produced plan missing the separation is a formatting defect,
the same class as a missing section.

**Cap the plan's own size.** Grounding, File map and Tasks together should
stay under roughly 300 lines for a plan with 2-4 tasks; a plan pushing past
~500 lines is a sign the work spans more than "one coherent deliverable"
(see C1) rather than a reason to write more prose per task. Prefer citing a
pattern once with a `file:line` over re-explaining it in every task that
uses it.

`**Slug:**` is machine-read: `tools/resume.py` keys every derived fact off
it — the plan, `refs/uaios/green/<slug>`, the attempt ledger. A plan named
after its feature while the branch is named after something else matches
nothing.

## The constitution gate

Every plan carries this block, tick or justify, never silent —
`.claude/constitution.md` holds the articles it names:

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

Two strings `tools/resume.py` reads as contract, not style:

| Marker | Meaning |
|---|---|
| `[NEEDS CLARIFICATION: q]` | an open question, inline where the answer belongs |
| `## Approved` | the user passed Gate 1 |

**A marker outranks approval.** While any remains, the derived state is
`WAITING_PLAN_APPROVAL` no matter what else the file says.

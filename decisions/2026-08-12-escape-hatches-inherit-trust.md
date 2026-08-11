# An escape hatch inherits the trust model of the thing it bypasses

Date: 2026-08-12

## Decision

A suppression marker is scoped to the clauses where a legitimate reason can
exist, and that scope is a table in code, not a judgement at the call site.

`tools/security_gate.py`:

```python
WAIVABLE_CLAUSES = ("control-weakened", "sensitive-unmapped")
```

The other three clauses — `secret-in-branch`, `agent-unscoped`,
`dependency-risk` — cannot be waived. A marker naming one of them is **reported
as blocking**, with the text `An inline allow was present and does NOT apply`,
rather than ignored: an author who wrote a waiver believes they have handled the
finding, and silence would confirm it.

## Why

The gate exists because a *receipt* — a record asserting that a review happened
— is the one shape this repository must not rebuild.
`pre-commit/03-review-gate.py` was exactly that, and it failed twice: every
receipt self-invalidated because the receipts file was tracked, and then the
model wrote one asserting a sign-off that had not happened. *"A forged receipt
and a real one are the same file."* Deleted 2026-08-02 under *"Every hook
verifies an artefact. Not one enforces process."*

So every clause of the gate is a fact about the artefact. Then an escape hatch
was added, modelled on ruff's `# noqa`, on the argument that it lives in the diff
a reviewer reads and can be recorded nowhere else.

That argument is sound, and it was generalised to all five clauses without being
re-tested per clause. `code-review` caught the result on the first pass:

    F1 waived-credential exit: 0 -> [('secret-in-branch', 'advisory')]

A committed credential plus one comment line beside it, and the gate returned
green — **a self-certified pass, which is the receipt's actual failure mode**
wearing the escape hatch's clothes. It also contradicted a rule shipped in the
same commit, `code-review/SKILL.md`: *"A high-severity security finding is never
auto-waived… `_hooklib.classify_failure` gives its class a budget of zero."*

The generalisable lesson, and the reason this is an ADR rather than a bug fix:
**a bypass is only as safe as the weakest thing it can bypass.** Justifying it
against the easiest case and applying it to all of them is the error, and it is
attractive because the easiest case is genuinely convincing — a regex legitimately
moves between tables, and forcing that through a review round would make the gate
something people route around.

The test is per clause: *can a legitimate reason exist?* For a pattern that moved
and a sensitive path the test map cannot express, yes — those are design
decisions, and a decision with its reason in the diff is exactly what should be
waivable. For a credential, an unscoped write capability, or a denied licence,
no. Each has a real fix that is not a comment.

## Alternatives considered

- **No escape hatch at all.** Rejected: `control-weakened` fires on legitimate
  refactors, and a gate that cannot be satisfied by correct work is a gate that
  gets removed from `project-checks.json` within a month. The 2026-08-02 hook
  purge is that outcome, measured.
- **Require the waiver to name a plan or an issue.** Rejected: it re-introduces
  the receipt indirectly. Nothing can check that the referenced artefact says
  what the waiver claims, so it buys ceremony rather than evidence.
- **Escalate a waived credential to advisory and let review catch it.** Rejected:
  it makes the gate's exit code depend on a human reading the output, which is
  the property that distinguishes a check from a suggestion. Article V's shape —
  a thing that could not be established is never a pass — applies to a thing that
  was waived by the party being checked.
- **Make the waiver list configurable per repository.** Deferred, not rejected.
  A repository with a genuine reason to waive `dependency-risk` is plausible; one
  with a reason to waive `secret-in-branch` is not. If it is ever added, the
  secret clause should not be configurable.

## Consequence

`tools/test_security_gate.py` asserts the split by iterating `CLAUSES` rather
than listing cases, so a clause added to `WAIVABLE_CLAUSES` without thought fails
a test that already exists. A waiver list is precisely the table that grows by
accident.

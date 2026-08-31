---
name: release-git
description: Land reviewed work in the repository, then get it running live. Covers branch, PR, rebase, merge, deploy, smoke check, SLOs, and rollback, with signals. Never pushes, merges, or deploys without explicit human approval. Triggers include "open a PR", "push this up", "merge it", "ship it", "resolve these conflicts", "deploy this", "go live", "roll it back", or "is this observable". Use this whenever reviewed work must reach the repository or a running target. Do NOT use to review the code (code-review), diagnose a failing check (debugging), or prove the change meets the brief (testing).
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task AskUserQuestion
---

# Release / Git

Two procedures, merged from the former `delivering` and `releasing`
skills — both own "get reviewed work into the world," one for the
repository, one for a running target. Same two-gate discipline throughout:
nothing here pushes, merges, or deploys on an inferred yes.

**Delivering** (below): prepare the reviewed change for safe repository
integration — branch, PR, rebase, merge. Does not deploy.

**Releasing**: read `references/release-procedure.md` for putting delivered work
into a running environment — deploy, smoke check, observe, rollback, and
<!-- GATE 2: shipment approval. The chain has two; see .claude/workflow.md. -->
**Gate 2**, the shipment approval via `AskUserQuestion`. Entered from
Delivering only when a deploy target exists.

Cap visible output at ~500 tokens.

## Delivering procedure

Prepare the reviewed change for safe repository integration. This stage may
create local commits, branch/PR metadata, and a merge-queue handoff according
to the host's contract. It does not deploy. Shipment approval remains the
second and final human gate, in the releasing procedure below.

<HARD-GATE>
Never integrate a change without current verification evidence, a passing
automated code review, clean secret checks, and a named base branch. Never use
model preference to choose between competing changes: promote the candidate
with objective checks, acceptance coverage, security status, scope fit,
rollback, and then the smallest lower-risk diff.
</HARD-GATE>

### Steps

1. Confirm the worktree/branch is isolated and the base is known. For parallel
   work, use one worktree per task and serialize shared-interface changes.
2. Run the repository's required all-tier checks and secret scan on the actual
   candidate. Preserve command, exit code, and relevant output as evidence.
3. **Before rebasing, know what it would do — without doing it.**

       git merge-tree --write-tree <base> <head>

   This composes a tree object and reports the result without touching the
   index or working tree — a real simulation, not a guess. Read the outcome
   as one of "no-op", `clean`, `conflict`, or `unknown`. **`unknown` is not
   `clean`** and is not licence to proceed as if it were.
4. If it reports `conflict`, classify the conflicting paths mechanically —
   never by eye. A lockfile or a purely generated file is `mechanical` and
   safe to resolve with bounded attempts; a migration, an auth path, or
   anything that doesn't clearly match a known-safe pattern is `substantive`
   and **escalates** — hand it to `debugging` as a structured incident rather
   than resolving it by guess.
5. Prepare the PR or merge-queue handoff. **Compose the description yourself
   from the plan's goal, its checked-off progress, the risk tier, and review
   findings — never from an auto-fill of squashed commit subjects.** Do not
   bypass protected-branch rules, required checks, or the merge queue. Do not
   deploy.
6. **Run the integration preflight and quote it. A failing exit code is a
   stop, not a note.**

       python tools/delivery_check.py --base <base> --head <head>

   Verifies seven facts: base alignment, CI green *for this exact SHA*,
   stack depth, merge-method compatibility, divergence from the base,
   worktree cleanliness, and whether each is even enforceable here. Exit
   `0` ready · `1` a check failed · `2` a fact could not be determined —
   and **`2` is not `0`**. Exit 1 is a stop, not a note.
7. **Before anything leaves the machine, confirm with `AskUserQuestion`.**
   See "The push confirmation" below — a prose question does not count.
8. Return `clean`, `conflict`, or `blocked` with changed paths, base, checks,
   conflict files, and evidence. Never `clean` without step 6's output quoted.

### The push confirmation

<HARD-GATE>
`git push`, opening a PR, and any merge are outward-facing and are **never**
performed on an inferred yes. Ask with `AskUserQuestion`, naming the remote, the
branch and the base in the question itself, with real options — push and open a
PR, keep it local, cancel.
</HARD-GATE>

**This is an operational safety check, not a third lifecycle gate.** Gate 1
approves a plan and Gate 2 (releasing procedure) approves a shipment; this
authorises one irreversible operation on the tree in front of you. It
carries no `<!-- GATE n -->` marker for that reason, and whatever this
project uses to validate its gate count should still expect exactly two.

#### Exception: a parallel round's task branches

**Scope, exactly:** branches `implementation` created for one round of
tasks `tools/parallel_groups.py` proved independent. For those branches
only, `git push` and PR-creation happen automatically, per branch, with no
`AskUserQuestion`. Nothing is merged by this step, each branch is small and
independently reviewable, and the round's own `refactoring`/`code-review`
pass still gates the merge (below).

Every other push in this repository keeps requiring the full per-instance
confirmation above, unchanged.

### Nothing here merges, and that is deliberate

**No skill in this layer runs the merge command — except the one narrow,
explicitly-gated case below.** In every other case this stage prepares the
candidate and stops; a human presses the button.

#### Exception: a parallel round's batched merge

Once every PR from a round is open, run one scoped `refactoring` +
`code-review` pass over the round's *combined* diff. Then present **exactly
one** `AskUserQuestion` naming every PR in the round and asking which, if
any, to merge now. On approval, merge each named PR with the GitHub MCP
tool `mcp__github__merge_pull_request` — never the CLI phrase this section
otherwise prohibits.

### Stacked PRs — state the merge strategy before you open the second one

A branch opened against another open PR's branch is a **stack**. Three
rules, in order of preference: prefer no stack; if you stack, merge with
merge commits, not squash; keep the stack shallow (past two or three, use
tooling — Graphite, `ghstack`, `spr` — not discipline). Check the base you
declare against the base you cut from:

```bash
[ "$(git merge-base origin/<base> origin/<head>)" = "$(git rev-parse origin/<base>)" ] \
  && echo aligned || echo MISMATCH
```

Full mechanics (the squash-merge failure table, recovery limits, the red-flags
table): `references/delivery-mechanics.md`.

### Delivering handoff

On a clean handoff, continue into the **Releasing procedure** below for
release readiness and the shipment approval gate. On conflict or failed
checks, invoke `debugging`.

## Releasing procedure

See `references/release-procedure.md` for the full procedure: the shipment gate,
`tools/release_candidate.py`, the three preconditions, target detection,
the irreversibility statement, the smoke check, post-release observation,
and roll-back-first-diagnose-second. Platform-specific commands live in
`references/PLATFORMS.md`; SLOs/alerts/runbooks in
`references/observability-sre.md`. After the smoke check, dispatch
`reviewer` (mode: release) for an independent readiness check when the
harness supports subagents.

Not every change needs it — skip when there is no environment and say so,
then go to `documentation`.

## Next step

**The terminal state is invoking `documentation`** — once released, or once
delivered for work with no deploy target. `LOG.md` records what version
went live (or that nothing needed to); `HANDOFF.md` carries the rollback
command forward when one exists.

## Routing

- Mandatory validator (delivering): all-tier checks, secret scan, review
  receipt, and base-branch evidence.
- Mandatory validator (releasing): the smoke check in `references/release-procedure.md`.
- Preceded by `code-review` — this consumes a change that has already been
  reviewed and verified.
- Terminal handoff: `documentation`, once released (or once delivered, for
  work with no deploy target).
- Failure handoff: `debugging`, on a failed check, a substantive conflict,
  or a failed release (after rollback, never before).
- Consult `engineering-standards` alongside `references/observability-sre.md`
  for what to actually monitor once a deploy target exists.

## Success

The candidate is reproducible, review-backed, conflict-safe, and integrated
without silently pushing, merging, or deploying around policy; and, when a
target exists, it is serving with a quoted smoke check, a rollback named
before the deploy, and `LOG.md` saying what went live where.

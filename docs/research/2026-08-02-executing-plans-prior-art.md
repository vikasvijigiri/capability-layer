# What should the stage-7 execution skill for this repo look like?

**Asked because:** `docs/workflow.md` stage 7 (Execution) is the last unowned
workflow stage. `writing-plans` gate 3 hands off to "a fresh `general-purpose`
agent" or "inline execution" and nothing describes either.
**Verdict:** build one skill, `executing-plans`, covering both modes. Adopt
superpowers' plan-critique-first / stop-don't-guess spine and minsky's
verify-outcomes-not-actions and spec-reconciliation rules. Skip the whole
subagent-orchestration apparatus — ledger files, workspace scripts, fix-round
caps, model-selection tiers — none of it is grounded here.

## Findings

**"Review the plan critically before executing" is the one step both families
open with.** HIGH — superpowers `executing-plans` Step 1 ("Review critically —
identify any questions or concerns … Raise them with your human partner before
starting"); `subagent-driven-development` widens it to a pre-flight scan for
tasks that contradict each other or the plan's Global Constraints, presented as
**one batched question** rather than an interrupt per discovery.
*Here:* adopted as the first step, with the batched-question rule. Our
`writing-plans` self-review already hunts the same class (Red Flags, type
consistency) but runs before approval — by execution time the plan may have been
edited.

**Verify outcomes, not actions.** HIGH — minsky `implement-task` §7: "Never
treat a command succeeding (exit 0, API 200) as proof the desired effect
occurred. Read back the result: query the setting you changed, count rows after
a migration, call the tool you registered." superpowers reaches the same place
from the other side ("Don't skip verifications", "Verification fails repeatedly
→ stop").
*Here:* this is CLAUDE.md's "never report a check as passing unless you ran it
and can quote its output" stated for execution, and it maps onto the repo's own
recurring failure — *prose declares a capability the wiring does not implement*,
7 instances. Became the HARD-GATE. Our sharpest local instance: a hook's symptom
of being broken is silence, identical to working, so `python tools/run_hook.py`
against a realistic payload is the read-back for any hook edit.

**Deviating from the plan mid-implementation must be reconciled, never left
implicit.** HIGH — minsky §Convergence-checklist item 5: if you deviate from a
stated design decision you MUST either update the spec with the rationale or
revert to it, "never leave an unreconciled spec-vs-impl divergence for the
reviewer to find". Its origin incident is precise: one file's convention comment
overrode a spec decision, costing a review round. superpowers' equivalent is
weaker — "return to review when the partner updates the plan".
*Here:* adopted verbatim in shape. The plan file is the artefact to amend, and
`writing-plans` already treats it as the implementer's only source of truth.

**Stop and ask; never force through a blocker.** HIGH — both superpowers files
list the same four stop conditions (blocker mid-task, plan gap, unclear
instruction, verification failing repeatedly) and both close with "stop when
blocked, don't guess". minsky routes the same class into its entry gate.
*Here:* adopted, with one local change — a *failing verification* is not a
question for the user, it is `systematic-debugging`'s trigger. Routing it to a
skill this repo already owns is stronger than superpowers' "raise it with your
partner", which is what a repo with no debugging skill has to say.

**A per-task commit is not free in this repo.** HIGH — verified by reading the
hooks, not by assumption. `pre-commit/03-review-gate.py` fires on every
`git commit`, `git push` and `gh pr create`, and its receipt is fingerprinted to
the exact content, so a receipt goes stale the moment the next task edits
anything. `pre-commit/05-docs-required.py` denies only at `MIN_FILES = 10`
staged files with neither `LOG.md` nor `HANDOFF.md` — so ordinary per-task
commits clear it, and I was wrong to expect otherwise before reading it.
*Here:* the plan's "Step 5: Commit" costs a `code-review` sign-off per task.
The skill states this and offers the two honest options (sign off per task, or
execute the run and commit once), rather than letting the run stall at a gate
nobody anticipated.

**Batch size at checkpoints is unsettled.** LOW — three positions in three
files. superpowers-canonical `executing-plans` executes *all* tasks then reports;
`aaddrick/claude-pipeline`'s fork of the same skill executes **the first 3
tasks**, reports, waits; `subagent-driven-development` forbids pausing entirely
("'Should I continue?' prompts and progress summaries waste their time").
*Here:* see Disagreements.

**The plan's checkboxes are already the progress record.** MEDIUM — superpowers
argues hard for a ledger *file*: "conversation memory does not survive
compaction … controllers that lost their place have re-dispatched entire
completed task sequences — the single most expensive failure observed."
*Here:* the need is real, the file is not. `writing-plans` mandates `- [ ]`
checkbox syntax on every step expressly "for tracking", `post-run/03-checkpoint.py`
snapshots the tree every turn, and `HANDOFF.md` is the cross-session state doc
that `knowledge-manager` owns. Ticking the plan file is the ledger; adding a
second one would create exactly the duplicate owner this repo keeps deleting.

**Irreversible steps need an in-conversation approval that no skill can grant.**
HIGH — CLAUDE.md's Never list, `writing-plans`' closing Routing line, and
`pre-commit/02-branch-guard.py` all say it independently.
*Here:* restated as a hard stop in the task loop, since execution is the only
stage that can actually reach a push or deploy.

## Disagreements

**Pause between tasks, or run to the end?** superpowers-canonical runs all tasks
then reports; its `claude-pipeline` fork batches 3 and waits; the subagent
variant forbids pausing at all. No source gives evidence, only a stance.

Leaned to: **execute a whole task without pausing, report one line at each task
boundary, and stop only on a blocker, an unreconciled deviation, or an
irreversible step.** Grounded locally rather than by vote — a task in a
`writing-plans` plan already ends with "an independently testable deliverable"
and is sized to be "worth a fresh reviewer's gate", so the task boundary is
where this repo's plans already put their seams. Mid-task check-ins have no
artefact to show.

**Where the fix loop lives.** `subagent-driven-development` builds an elaborate
one: five rounds, model escalation at round 4, a breaker that forces
adjudication, every ruling written to a ledger. Not adopted — it is machinery for
a controller that cannot see the code it is reviewing. Inline, a failing
verification goes to `systematic-debugging`, which already has a four-phase loop
and writes `ISSUES.md`.

## Not adopted

- **A separate `subagent-driven-development` skill.** The repo's standing rule is
  not to spawn subagents unless asked; `writing-plans` gate 3 is where the user
  asks. One skill with a mode section beats two skills where one is dormant.
- **`scripts/sdd-workspace`, `task-brief`, `review-package` helper scripts** and
  the `.superpowers/sdd/<plan>/` workspace — infrastructure for keeping subagent
  output out of the controller's context. Real problem, but it presupposes the
  fan-out we are not doing.
- **Model-selection tiers per role.** Concrete and well argued, but this repo has
  never dispatched an implementation subagent; tuning cost tiers for a path with
  zero runs is speculative.
- **Five-round fix cap with escalation and a breaker.** See Disagreements.
- **minsky's entry gate on task status** (`TODO/PLANNING → halt`) — it rests on
  an MCP task database. Our equivalent is simply: no approved plan file, no
  execution.
- **minsky's convergence checklist in full** (trust-boundary coverage, portable
  defaults, probe-before-defer, per-AT evidence, negative controls). Excellent,
  and almost all of it is review-time concern that `code-review` owns here.
  Two items were lifted because they are execution-time: verify-outcomes and
  spec reconciliation. **Probe before deferring** — don't write "requires X
  access" without running `which x` first — is worth a future `code-review` or
  `knowledge-manager` line and is recorded here rather than smuggled in.

## Sources

- [obra/superpowers `skills/executing-plans/SKILL.md`](https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md) — read in full
- [obra/superpowers `skills/subagent-driven-development/SKILL.md`](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md) — read in full
- [aaddrick/claude-pipeline `.claude/skills/executing-plans/SKILL.md`](https://github.com/aaddrick/claude-pipeline/blob/main/.claude/skills/executing-plans/SKILL.md) — read in full; a fork of the first that batches 3 tasks
- [edobry/minsky `.claude/skills/implement-task/SKILL.md`](https://github.com/edobry/minsky/blob/main/.claude/skills/implement-task/SKILL.md) — 71k chars; §Process, §4-§7, §Convergence checklist, §Constraints, §Key principles, §Regression examples read directly
- `mcp__github__search_code`: 513 repos carry `.claude/skills/executing-plans/SKILL.md`; 305 carry `subagent-driven-development`. Spot-checked one (`claude-pipeline`) to see how much forks diverge — barely.
- This repo, read before searching: `docs/workflow.md` stage 7, `HANDOFF.md`
  Pending (which names this gap), `.claude/skills/writing-plans/SKILL.md` gate 3,
  `.claude/skills/code-review/SKILL.md`, `.claude/hooks/pre-commit/03-review-gate.py`,
  `.claude/hooks/pre-commit/05-docs-required.py`, `.claude/settings.json`,
  `docs/specs/2026-08-01-evidence-ledger-design.md`.

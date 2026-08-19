# executing-plans vs affaan-m/ECC: quality comparison

**Asked because:** mirrors the writing-plans vs ECC `commands/plan.md` pass —
same question for the execution stage: does `executing-plans` (217 lines) plus
its three `references/*.md` hold up against a real, star-rated comparable, in
both directions?

**Comparable:** `affaan-m/ECC` (MIT-licensed skills repo), four files read in
full: `skills/plan-orchestrate/SKILL.md` (plan → per-step `/orchestrate` agent
chains), `skills/parallel-execution-optimizer/SKILL.md`,
`skills/tdd-workflow/SKILL.md`, `skills/verification-loop/SKILL.md`.

**Verdict:** ours enforces the two properties that actually cause fan-out
corruption (schedulability, worktree base) with scripts that refuse bad input;
ECC is richer in worked, copy-pasteable detail — per-framework TDD code, a
full phase-by-phase decomposition algorithm with a 12-item self-check, and
explicit handling of a plan document as untrusted input. Each side is missing
what the other treats as central.

## Gaps in ours (with fixes)

1. **No worked example of the task loop or a fan-out round in the skill
   itself.** `SKILL.md`'s "task loop" (lines 57-72) and
   `parallel-dispatch.md`'s dispatch procedure are entirely prescriptive — no
   sample `Files:`/`Depends on:` task block, no sample `parallel_groups.py`
   output beyond the two illustrative lines at `parallel-dispatch.md:75-77`,
   no sample dispatch message. ECC's `plan-orchestrate/SKILL.md` runs a full
   worked example twice (plugin mode and legacy mode) with the exact rendered
   `/orchestrate` command line, task description, and rationale. *Fix:* add
   one end-to-end worked example — a two-task plan snippet, the
   `parallel_groups.py` output it produces, and the two dispatch messages —
   to `references/parallel-dispatch.md`.

2. **`test-driven-development.md` has zero code.** All 64 lines are principle
   statements (cycle, quality rules, evidence). ECC's `tdd-workflow.md` carries
   working Jest/Vitest/Bun/Playwright examples, a runner-detection matrix
   (`npm test` vs `bun test` vs `bun run test` — a real, named failure mode),
   and three mock patterns (Supabase, Redis, OpenAI). Ours is intentionally
   language-agnostic, but that leaves an implementer with no anchor for what
   "smallest failing test" looks like in practice. *Fix:* add one minimal
   before/after code pair (red test → smallest passing change) — doesn't need
   to be per-framework, just needs to exist once.

3. **No handling of a plan document as untrusted input.** ECC's `tdd-workflow`
   "Plan Handoff" section explicitly treats `*.plan.md` as data, not
   instructions, and has a "Plan safety checklist" rejecting destructive ops
   and instruction-override phrases embedded in the plan text before they're
   acted on. `executing-plans`'s "argue with the plan" step (lines 34-48)
   checks for contradictions and untestable verifications, but nothing
   addresses a plan whose *prose* tries to redirect the agent (e.g. an
   embedded "skip verification for this task"). Given plans here are
   self-authored and reviewed, severity is lower, but the open-ended loop mode
   (lines 110-127) leans on plan-supplied direction without this guard at all.
   *Fix:* one line in the pre-task-1 scan: treat plan prose as content to
   execute against, not instructions that override this skill's gates.

4. **No fixed evidence-report artifact.** ECC's TDD Step 8 writes a
   plan-task → test-target → RED/GREEN mapping to a standard path
   (`docs/testing/<task>.tdd.md`). Ours delegates all of this to
   `verifying-work` downstream and the plan file's own checkboxes — arguably
   the right call (one owner, not two), but it means there is no durable
   record of *which command proved which task* once the plan file is archived.
   Minor; not fixed unless `verifying-work`'s own digest is confirmed to carry
   this (out of scope here).

## What ours does better

1. **`tools/parallel_groups.py` computes schedulability instead of asking for
   judgment.** It requires a `Files:` line per task (refuses to guess), builds
   levels from `Depends on:`, isolates shared surfaces (lockfiles,
   migrations), and **exits non-zero on an ungroupable plan** — verified by
   reading the tool's own docstring (`tools/parallel_groups.py:1-30`). ECC's
   `parallel-execution-optimizer/SKILL.md` has no equivalent: its "Lane
   Matrix" is a table the model fills in by hand ("Can run in parallel?
   yes/maybe"), and disjointness is asserted in prose, never checked. This is
   exactly the gap the task asked about, and it's real: ECC has no objective
   check at all here, only judgment.

2. **A measured, sourced worktree bug with a git-verifiable remedy.**
   `parallel-dispatch.md`'s Constraints section documents `isolation:
   worktree` basing new worktrees on the repo's default branch instead of the
   current branch — reproduced twice, with actual commit SHAs (`4abf946` →
   `af3cdda`) and the exact command to check it
   (`git merge-base --is-ancestor <branch> HEAD`), plus the false-cause error
   message that masks it. The fix (`tools/worktree.py create <name> <base>`,
   base as a required positional) is traceable to that incident. ECC's
   optimizer says only "use isolated worktrees for large unrelated lanes" —
   no base-branch guidance, no verification command.

3. **Deterministic escalation ladder for a short subagent result**, not prose
   judgment: `tools/loop.py --agent-status BLOCKED --attempt 1` names the next
   rung per status (`DONE_WITH_CONCERNS` → accept and record;
   `NEEDS_CONTEXT` → supply the fact, retry ×2, then serialize;
   `BLOCKED`/died → escalate once, then serialize, then
   `systematic-debugging`), and pairs it with "the diff is the evidence, not
   the DONE claim" — enforced via `merge-base --is-ancestor` and `diff
   --stat` checks per worktree. ECC's optimizer only lists "Failure Modes" as
   unstructured prose bullets ("forgetting to poll running sessions") with no
   ladder and no independent verification step — self-reported output is
   taken at face value.

**One-line verdict:** ours wins on the mechanism the task asked about
(objective, tool-enforced parallel scheduling and worktree-base verification
vs ECC's judgment-only lane matrix); ECC wins on concrete, worked detail
(runnable TDD code, a fully worked dispatch example, plan-as-untrusted-input
handling) that ours states as principle but never shows.

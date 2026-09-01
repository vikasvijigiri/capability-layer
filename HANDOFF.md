# Handoff

<!-- session-context:start -->

## Resume here

Branch `feat/knowledge-doc-head-contract` implements the knowledge-doc head
contract — plan `docs/plans/2026-09-01-knowledge-doc-head-contract.md`, tasks
0–8 done. **Next: task 9** — `python tools/run_checks.py --tier all
--require-test`, run the hook with `{}` to confirm it injects only the marked
heads and authors nothing, write the `LOG.md` entry, then open the PR.
`main` is at `8b0bb85`; no other open PRs or branches in flight.

## Decisions (don't relitigate)

- Session-start reads a **bounded, delimited head** of TASK/HANDOFF/LOG,
  verbatim, never a whole-file clip — `decisions/2026-09-01-knowledge-doc-head-contract.md`.
- `TASK.md` is a capped ≤6-row ledger, not an append-only trail; evicted
  tasks live on in `LOG.md` + `docs/plans/`. Pre-2026-09 history is
  `docs/archive/task-log-pre-2026-09.md`.
- Domain-knowledge skills are consulted, not given a lifecycle stage —
  `decisions/2026-08-31-knowledge-skills-consulted-not-staged.md`.
- Two approval gates only (`ExitPlanMode`, `AskUserQuestion`); branch-per-
  parallel-task is the standing default.

## Blocked / needs a human

nothing

<!-- session-context:end -->

## Known open items (not blocking)

- `ISSUES.md` carries two `0x08` bytes in the entry describing `0x08` bytes
  — see `ISSUES.md` 2026-08-11 21:15.
- `tools/resume.py`'s `BRANCH_PREFIX` strips only `feat/` while
  `_hooklib.active_plans()` strips five prefixes — `resume.py` can't resolve
  a plan on a `fix/`|`docs/`|`chore/`|`refactor/` branch. Its own unit.
- The "five state reporters" overlap (`/wip`, `/git-state`, `/handoff`,
  `resume.py`, `03-state-report.py`) — folding `/git-state` into `/wip` was
  tried and reverted; the bodies don't overlap. Needs its own decision.
- Gate 2 (`AskUserQuestion` shipment approval) has never fired end to end.
- The stale `TASK.md` "world-class SessionStart bootstrap scaffolding"
  In-Progress entry was subsumed by this plan and archived, not carried.

## Ruled out

- A dedicated lazily-read task-archive file the hook consults — a junk
  drawer nothing on the hot path reads; `LOG.md` + `docs/plans/` + git
  already answer "what shipped, when".
- Branch protection on this repo tier — `403 Upgrade to GitHub Pro`.

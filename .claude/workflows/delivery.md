# W5 — Large Engineering / Delivery

Notion's shape: Discovery → architecture → parallel independent work where
justified → implementation → integration → verification → security/quality
gates → release.

**This is stages 6-8 of the full chain, plus the parallel-dispatch
mechanism** — the one part of W5 the other four `workflows/*.md` files
don't cover:

- Stages 6-8 (`code-review` → `release-git`'s delivering procedure →
  `release-git`'s releasing procedure): read `.claude/workflow.md`'s stage
  table rows 6-8.
- Parallel independent work: read `python tools/parallel_groups.py <plan>`
  (which tasks may run together) and
  `decisions/2026-08-21-branch-per-parallel-task.md` (why branch-per-task
  is the default for a concurrent round, and how the batched merge
  question works). `implementation/references/parallel-dispatch.md`
  carries the dispatch mechanics.

Discovery/architecture at the front of W5 are stages 1-2 —
`universal-task.md` already covers them; not repeated here.

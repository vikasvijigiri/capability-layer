# Archive — retired content

Most of this directory is the UAIOS design as it stood **before** the
capability layer was collapsed on 2026-08-01 (commit `1443ba2`). It is kept
because it holds design intent that nothing else records, and moved here because
`CLAUDE.md` had been pointing readers at it with the warning "stale, read with
suspicion" — which is not a state a bootloader should leave a reader in.

`task-log-pre-2026-09.md` is the one exception in kind: retired *project
state*, not design — the pre-2026-09-01 `TASK.md` (former `## Active` entries,
all terminal, plus the old `## Completed` archive), moved out when `TASK.md`
became a capped ≤6-row ledger.

**Nothing here describes what currently runs.** For that, read
`.claude/workflow.md` (the stage → skill chain) and `CLAUDE.md` (the bootloader).

| Archived | What it was | What replaced it |
|---|---|---|
| `00-vision.md` … `17-extension-guide.md` | 18 chapters specifying an operating system of "engines" — blueprint, planning, token/time/cost optimizer, validation, quality, learning, observability, governance | The ten skills in `.claude/skills/`. Most engines were never built; the ones that were are hooks, not engines |
| `README.md` | The index for those 18 chapters | This file |
| `UAIOS.md` | A large ASCII architecture diagram of the whole system | `.claude/workflow.md`'s handoff graph, which describes what exists |
| `architecture-diagram.md`, `diagrams/*.mmd` | Per-plane Mermaid sources split out of that diagram | Same |
| `skill-structure.md` | A proposed 20-field skill schema (`average_latency`, `average_cost`, `success_rate`, `confidence`, `benchmarks`…) | The real frontmatter: `name`, `description`, `effort`, `model`. `tools/test_process_router.py` asserts it |
| `task-log-pre-2026-09.md` | The pre-2026-09-01 `TASK.md` — stale `## Active` entries (all merged/closed) and the append-only `## Completed` archive | `TASK.md`, now a capped ≤6-row ledger; `LOG.md` + PRs for delivery history |

Two ideas here were never implemented and are still worth their own decision
rather than silent disposal:

- **Domain skill packs** (`16-domain-skill-packs.md`) — independently
  rediscovered on 2026-08-02 as the mechanism that makes the pipeline
  domain-generic. See `docs/research/2026-08-02-generic-pipeline-skillset.md`.
- **Token / time / cost optimizers** (`08`–`10`) — the token half now exists in
  a much smaller form as `post-tool/01-context-budget.py`.

Do not edit anything in this directory. If a claim here becomes true again, move
it out and wire it up.

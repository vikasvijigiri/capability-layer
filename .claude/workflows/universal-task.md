# W1 — Universal Task

Notion's shape: INTAKE → CLASSIFY → CONTEXT BUDGET → ROUTE → EXECUTE →
VERIFY → REPAIR/ESCALATE if needed → FINALIZE.

**This is the full chain.** Read `.claude/workflow.md`'s stage table (all 9
rows) and its "State machine and failure loop" section — that file owns
the sequence, the entry rule, and the recovery ladder. Nothing here
restates it; a second copy is exactly the mistake
`decisions/2026-08-07-one-workflow-engine.md` records and forbids.

Default entry: any named request that isn't small enough to skip planning
(`.claude/workflow.md` §Entry, `entry-unframed`/`entry-open`).

# Escalation policy

Part of Notion §24's "Policy Gate" — what happens when a dispatched agent
or a check does not simply succeed.

**The rung ladder**: `python tools/loop.py --agent-status <status>
--attempt <n>` decides the next rung — supply, escalate, serialize, or
diagnose — from the agent's reported status and the attempt count.
`BLOCKED` escalates the model once and is never re-dispatched unchanged;
the serialize rung pulls the task into the main context and is offered
exactly once.

**Failure-class budgets**: `_hooklib.FAILURE_BUDGETS` — security 0 (never
retried), merge 2, transient 2, deterministic 3, unknown 3 — classified by
`_hooklib.classify_failure()`, first-match-wins, deterministic outranking
transient on purpose.

**Kill switch**: `python tools/halt.py --halt "<reason>"` — while halted,
`pre-tool/01-halt-guard.py` denies every state-changing or work-spawning
tool. Reads stay allowed so a halt can be investigated. `--resume` lifts
it.

Nothing here restates any of the three mechanisms; each is code.

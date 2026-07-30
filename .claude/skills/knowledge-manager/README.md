# Knowledge Manager

Owns the format and upkeep of a repo's persistent engineering docs:
`TASK.md`, `PLAN.md`, `MEMORY.md`, `HANDOFF.md`, `LOG.md`, and decision
records. The Repository Bootstrap hook creates these as empty skeletons;
this skill defines what belongs inside once there's real content, and
what never belongs there (git history, conversation transcripts,
temporary notes).

Does **not** own `CLAUDE.md` — that's the project handbook, created by the
bootstrap hook and kept current by the model directly during normal work
(see this repo's `CLAUDE.md`).

`workflow-orchestrator` invokes this skill's formats during Plan and
Knowledge Update; it doesn't restate them.

See [`SKILL.md`](SKILL.md) for the exact shape of each file.

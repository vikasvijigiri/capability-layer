# Workflow Orchestrator

Coordinates any non-trivial engineering request through one fixed pipeline:

```
Understand → Load Context → Plan → Execute → Review → Knowledge Update → Git Ready → Ship Ready → Done
```

It's the connective tissue between the other three skills — it classifies
the request, decides how much context to load and whether tasks run
sequentially or in parallel, then delegates:

- Task/plan **format** → `knowledge-manager` (this skill just fills it in)
- Quality gate → `code-review`
- Standards a change is judged against → `engineering-policy`
- Ship Ready only applies when the repo actually has a deployment target
  (e.g. Vercel) — skipped otherwise, not manufactured.

Deliberately skipped for trivial asks — a one-line fix doesn't need a
9-stage pipeline, and running it anyway would cost more tokens than it
saves.

See [`SKILL.md`](SKILL.md) for the full pipeline definition.

# Error Recovery

A bounded diagnose-fix-reverify loop for a failing check (build/test/deploy/API error).
Not a retry wrapper: it narrows context per attempt, never repeats a hypothesis a prior
attempt already falsified, and hands a finished record to `knowledge-manager`'s
`ISSUES.md` — one entry per incident, covering the whole attempt sequence, not one
append per attempt.

Reusable standalone, not just inside `mvp-builder`: any tough bug in an ordinary
interactive session fits this skill.

See [`SKILL.md`](SKILL.md) for the exact give-up conditions (bounded attempts, or a
repeated hypothesis) and the `ISSUES.md` → `MEMORY.md` promotion rule for a resolved
incident that reveals a durable, reusable lesson.

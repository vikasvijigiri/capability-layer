---
description: Create a durable session handoff from the repository's actual branch, task, verification, pending, and next-step state.
---

# Handoff

Mode: read-only
Arguments: optional focus hint in `$ARGUMENTS`.

Read `git status --porcelain=v1 -uall`, `TASK.md`, `HANDOFF.md`, `LOG.md`, and
`ISSUES.md` if present. Report current work, completed evidence, blockers,
open questions, exact changed areas, and the next concrete action. Do not edit
handoff documents; this command reports drift for `knowledge-manager` to record.

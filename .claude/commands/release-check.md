---
description: Verify release readiness through artifact identity, smoke checks, health signals, observation, rollback readiness, and residual-risk ownership.
---

# Release Check

Mode: read-only
Arguments: `$ARGUMENTS` identifies the release version and environment.

Run only approved non-destructive release checks. Confirm the exact artifact,
environment, smoke result, health signal, observation window, rollback path, and
risk owner. Dispatch `release-verifier` when available. Return PASS, FAIL, or
BLOCKED with timestamps and quoted evidence.

Do not deploy, rollback, mutate production, or declare success without health
evidence.

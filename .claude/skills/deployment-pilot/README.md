# Deployment Pilot

Deploys a reviewed build to the free-cloud host `stack-selector` chose, provisions
secrets (generating what it safely can, escalating what it can't), wires a `/health`
endpoint and basic logging, and verifies the live URL against the PRD's acceptance
criteria rather than a generic smoke check.

Owns the **repo-visibility default** (private, always, unless the goal explicitly said
otherwise) and the **generatable-vs-must-supply secrets split**. Distinct action space
from `code-review`/`git_delivery_guard.py` — this skill provisions billable
infrastructure, they review and gate code.

Reusable standalone, not just inside `mvp-builder`: any deploy task fits this skill.

See [`SKILL.md`](SKILL.md) for the exact autonomy defaults and how it hands unresolved
blockers (a denied deploy command, a missing third-party key) to `error-recovery`.

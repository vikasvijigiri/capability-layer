---
name: security-authz-check
model: sonnet
description: Reviews endpoints/resources for missing or inconsistent authorization checks (broken object-level authz, privilege escalation paths). Use for "check authorization", "can a user access another user's data", "authz review", "privilege escalation check", "can users see other people's data", "check the permissions", "is this endpoint protected", "could someone access what they shouldn't". Prefer this over trusting the UI to hide things - authorization holes are found at the API, not the screen. Do NOT use for authentication (login/identity) review — that's a distinct concern from authorization (permissions). A single targeted scan; for a full adversarial review of a pending diff, use `code-review` or the `security-reviewer` agent.
---

# Authorization Check Skill

Reviews each entry in `endpoints` against `role_model` for missing ownership checks or role-gating gaps (broken object-level authorization).

## When to use
- "check authorization", "can a user access another user's data", "privilege escalation check"

## Steps
1. For each endpoint, identify which role/ownership check should gate it per `role_model`.
2. Verify the check is actually enforced server-side (not just hidden in the UI).
3. Return `authz_findings` for any endpoint missing or inconsistently applying its check.

## Notes
A client-side-only restriction (hidden button, disabled UI) is not an authorization control — always require a server-side enforcement point.

## Routing

**Validator (required): `.claude/validators/security-secrets-scan.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

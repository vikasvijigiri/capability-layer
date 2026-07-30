> **Superseded.** The canonical copy of this file is `.claude/blueprints/backend-oauth.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# OAuth Blueprint — backend/blueprints/oauth-blueprint.md

Problem Signature

- Setup OAuth for first-party API requiring Google OIDC and refresh token rotation.

Preconditions

- Organization OAuth client registration permission
- Secrets vault available for client secret storage

Solution Workflow

1. Generate config via `oauth-skill`.
2. Validate config with `oauth-validator`.
3. Provision ephemeral test environment (manual approval).
4. Run integration tests.
5. Store validated config in `blueprints/` with metadata and evidence.

Why it works

- Encapsulates steps, validators, and human checkpoints to avoid accidental live changes.

Failure cases

- Missing permissions
- Invalid redirect URIs

Confidence: Medium
Reusability: High for similar API setups

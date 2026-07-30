> **Superseded.** The canonical copy of this file is `.claude/playbooks/backend-oauth.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# OAuth Playbook — backend/playbooks/oauth-playbook.md

Purpose: human-run steps to safely provision OAuth in production.

Steps

1. Read `oauth-blueprint.md` and confirm preconditions.
2. Run `oauth-skill` to generate config.
3. Run `oauth-validator` locally.
4. Request approval from Security team.
5. Provision in staging, run integration tests.
6. On success, provision in production with monitoring.

Rollback

- Revoke client secret and rotate keys if provisioning fails.

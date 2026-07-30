# OAuth Playbook — .claude/playbooks/backend-oauth.md

Purpose: human-run steps to safely provision OAuth in production.

Steps

1. Read `oauth-blueprint.md` and confirm preconditions.
2. Run `backend-oauth` to generate config.
3. Run `.claude/validators/backend-oauth.md` locally.
4. Request approval from Security team.
5. Provision in staging, run integration tests.
6. On success, provision in production with monitoring.

Rollback

- Revoke client secret and rotate keys if provisioning fails.

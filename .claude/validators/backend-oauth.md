# OAuth Validator — .claude/validators/backend-oauth.md

Purpose: validate OAuth configuration before provisioning or promotion.

Checks

- `client_id` and `client_secret` present and stored in vault
- Redirect URIs conform to allowed patterns
- Scopes requested are minimal and justified
- Test redirect endpoint returns 200 in ephemeral test environment

Failure handling

- Block provisioning and require human review
- Emit remediation steps and evidence
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "backend-oauth", "capability": "backend"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if a new blueprint/config artifact was produced.

Usage

Add this validator as a required gate in `.claude/workflows/backend-oauth.md`.

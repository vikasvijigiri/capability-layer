> **Superseded.** The canonical copy of this file is `.claude/validators/deployment-smoke-test.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Smoke Test Validator — deployment/validators/smoke-test.md

Purpose: run basic smoke tests against a deployment to ensure health.

Checks

- Endpoint health (200)
- Key flows succeed (login, read, write)

Failure handling

- Block promotion and trigger rollback plan
- Provide failure evidence
- Run `python tools/run_hook.py on-deploy-failure --file payload.json` (payload: `{"validator": "smoke-test", "capability": "deployment"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` for any promoted deployment record.

Usage

Include in `deploy-pipeline` as a required validator, and as the gate for any deployment-capability skill that changes live infra (`rollback`, `canary-promotion`, `secrets-provisioning`, `health-check-endpoint`, `infra-provision`).

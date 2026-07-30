# Smoke Test Validator — .claude/validators/deployment-smoke-test.md

Purpose: run basic smoke tests against a deployment to ensure health.

Checks

- Endpoint health (200)
- Key flows succeed (login, read, write)

Failure handling

- Block promotion and trigger rollback plan
- Provide failure evidence
- Run `python tools/run_hook.py on-deploy-failure --file payload.json` (payload: `{"validator": "deployment-smoke-test", "capability": "deployment"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` for any promoted deployment record.

Usage

Include in `.claude/workflows/deployment-pipeline.md` as a required validator, and as the gate for any deployment-capability skill that changes live infra (`rollback`, `canary-promotion`, `secrets-provisioning`, `health-check-endpoint`, `infra-provision`).

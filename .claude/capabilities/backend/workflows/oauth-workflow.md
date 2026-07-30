> **Superseded.** The canonical copy of this file is `.claude/workflows/backend-oauth.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# OAuth Workflow — backend/workflows/oauth-workflow.md

Purpose: full workflow to provision, test and validate OAuth integration.

Stages

1. Plan: use `oauth-skill` to generate configuration.
2. Validate: run `oauth-validator` (smoke checks + redirect verification).
3. Provision: (optional) invoke MCP to apply infra (requires human approval).
4. Test: execute integration tests.
5. Promote: mark blueprint if repeated and successful.

Safety

- Step 3 (Provision) requires human approval and preflight validators.
- Always run validators before applying side-effects.

Outputs

- `deployment_plan.md`
- `integration_test_report.json`

# OAuth Workflow — .claude/workflows/backend-oauth.md

> **How to run this.** This is a document you follow, not an executable. Claude Code
> has no workflow runtime. The owning skill routes here; read the steps, run each with
> the Skill or Agent tool, and finish with the validator named below.


Purpose: full workflow to provision, test and validate OAuth integration.

Stages

1. Plan: use `backend-oauth` to generate configuration.
2. Validate: run `.claude/validators/backend-oauth.md` (smoke checks + redirect verification).
3. Provision: (optional) invoke MCP to apply infra (requires human approval).
4. Test: execute integration tests.
5. Promote: mark blueprint if repeated and successful.

Safety

- Step 3 (Provision) requires human approval and preflight validators.
- Always run validators before applying side-effects.

Outputs

- `deployment_plan.md`
- `integration_test_report.json`

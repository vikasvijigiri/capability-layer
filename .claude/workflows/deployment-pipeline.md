# Deploy Pipeline — .claude/workflows/deployment-pipeline.md

> **How to run this.** This is a document you follow, not an executable. Claude Code
> has no workflow runtime. The owning skill routes here; read the steps, run each with
> the Skill or Agent tool, and finish with the validator named below.


Purpose: CI/CD pipeline with canary, smoke tests and rollbacks.

Stages

1. Build artifacts
2. Deploy canary
3. Run smoke tests and metrics checks
4. Promote or rollback

Validators

- Smoke tests
- SLO checks
- Cost budget checks

Safety

- Auto-rollback on failing smoke tests or SLO regressions.

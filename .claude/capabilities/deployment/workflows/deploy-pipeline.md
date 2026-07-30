> **Superseded.** The canonical copy of this file is `.claude/workflows/deployment-pipeline.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Deploy Pipeline — deployment/workflows/deploy-pipeline.md

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

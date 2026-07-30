> **Superseded.** The canonical copy of this file is `.claude/blueprints/deployment-canary.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Canary Deployment Blueprint — deployment/blueprints/canary-blueprint.md

Problem Signature

- Safely roll out a change with limited exposure and automatic rollback.

Solution

1. Deploy canary subset
2. Monitor SLOs and metrics
3. Promote when metrics stable
4. Roll back automatically on regressions

Reusability: High
Confidence: High

# Canary Deployment Blueprint — .claude/blueprints/deployment-canary.md

Problem Signature

- Safely roll out a change with limited exposure and automatic rollback.

Solution

1. Deploy canary subset
2. Monitor SLOs and metrics
3. Promote when metrics stable
4. Roll back automatically on regressions

Reusability: High
Confidence: High

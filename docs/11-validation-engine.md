# 11 — Validation & Verification Engine

## Purpose
Ensure outputs meet requirements, are factual, safe, and auditable.

## Validation Types
- Requirement checks (acceptance criteria)
- Fact-checking and source verification
- Security and privacy checks
- Performance and resource checks

## Workflow
1. Define validators per task
2. Run validators post-execution
3. Emit structured results and remediation steps

## Gate rules
- Block or flag side-effects when validation fails
- Auto-rollbacks or manual remediation flows
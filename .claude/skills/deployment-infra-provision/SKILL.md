---
name: deployment-infra-provision
model: haiku
description: Generates infrastructure-as-code templates and a provisioning plan for a target environment. Use for "provision this infra", "generate terraform/cloudformation", "set up a new environment", "IaC template for this stack", "we need staging", "spin up the infrastructure", "write the terraform". Prefer this over clicking through a cloud console - unreproducible infrastructure cannot be rebuilt or reviewed. Do NOT use to actually apply/deploy — that requires a human-approved workflow. One step of a release; for an end-to-end deploy with secrets, health checks and live-URL verification, use `deployment-pilot`.
---

# Infra Provision Skill

Generates IaC templates and a dry-run plan for provisioning resources — never applies changes itself.

## When to use
- "provision infra", "generate terraform/cloudformation", "set up environment", "IaC template"

## Steps
1. Validate environment and quotas.
2. Generate IaC templates (Terraform/CloudFormation snippets).
3. Run a plan/dry-run to verify the diff.
4. Return `plan` + `templates`.

## Notes
Applying changes requires human approval plus the cost-estimate and policy validators — never done inside this skill.

## Routing

**Validator (required): `.claude/validators/deployment-smoke-test.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/deployment-canary.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/deployment-pipeline.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

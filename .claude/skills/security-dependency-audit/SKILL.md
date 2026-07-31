---
name: security-dependency-audit
model: sonnet
description: Checks project dependencies against known CVE/advisory databases and flags outdated or vulnerable packages. Use for "check dependencies for vulnerabilities", "any known CVEs", "is this package safe to use", "dependency audit", "are our packages safe", "any known vulnerabilities", "is this library ok to use", "check for CVEs". Prefer this over assuming a popular package is safe - popularity and patch status are unrelated. Do NOT use to auto-upgrade packages — report only, human decides the upgrade path. A single targeted scan; for a full adversarial review of a pending diff, use `code-review` or the `security-reviewer` agent.
effort: medium
---

# Dependency Audit Skill

Checks packages declared in `manifest_files` against known advisories and flags outdated majors with available patches.

## When to use
- "check dependencies for vulnerabilities", "any known CVEs", "dependency audit"

## Steps
1. Parse `manifest_files` for direct and transitive dependencies.
2. Cross-reference against known advisory data (e.g. `npm audit`, `pip-audit`, `osv`).
3. Return `dependency_findings` ranked by severity, with the minimal safe version bump per entry.

## Notes
Never auto-apply a major version bump — flag it and let a human confirm no breaking change is introduced.

## Routing

**Validator (required): `.claude/validators/security-secrets-scan.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

# Security Capability Package

Purpose: adversarial review and hardening — injection, secrets exposure,
authorization gaps, dependency risk — backing the `security-reviewer` agent.

Keywords: security, vulnerability, injection, sql injection, xss, secrets, exposed credentials, authz, authorization, auth bypass, dependency vuln, cve, exploit, is this safe, security review, penetration, owasp

Entry point: load this file for `security` tasks. It declares read-only
review skills; fixes are applied by the owning capability (`backend`/
`frontend`), never by these skills directly.

Layout


Routing

Findings-only: these skills report, they do not patch. Always run
`.claude/validators/security-secrets-scan.md` on the findings report, then route fixes back to
`backend`/`frontend` capabilities and re-run that capability's own validator.

Skills

The 3 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `security-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `security-authz-check`
- `security-dependency-audit`
- `security-injection-scanner`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`security-`. The copies still under `capabilities/security/` are superseded and
must not be linked to.

- `.claude/validators/` — `security-secrets-scan`

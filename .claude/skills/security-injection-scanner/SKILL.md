---
name: security-injection-scanner
model: sonnet
disallowed-tools: Edit, Write, NotebookEdit
description: Scans input-handling code paths for injection risk (SQL, command, template, NoSQL, LDAP) by tracing untrusted input to sinks. Use for "check for injection", "sql injection risk", "is this input sanitized", "can this be exploited", "is this input safe", "could someone break this with input", "we build a query from user input". Prefer this over reading the query by eye - tracing untrusted input to a sink is what finds the reachable path. Do NOT use to apply the fix — report only, per this capability's read-only design. A single targeted scan; for a full adversarial review of a pending diff, use `code-review` or the `security-reviewer` agent.
effort: medium
---

# Injection Scanner Skill

Traces untrusted input from entry point to sink (query, shell command, template render) across `code_paths`, flagging any unsanitized/unparameterized path.

## When to use
- "check for injection", "sql injection risk", "can this be exploited"

## Steps
1. Identify entry points accepting untrusted input in `code_paths`.
2. Trace each to its sink (DB query, shell exec, template, deserializer).
3. Flag any sink not using parameterization/escaping/allow-listing.
4. Return `injection_findings` with severity and the exact vulnerable line.

## Notes
Report-only — never patch the finding here; hand it to `backend-engineer`/`frontend-engineer` and re-scan after the fix.

## Routing

**Validator (required): `.claude/validators/security-secrets-scan.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

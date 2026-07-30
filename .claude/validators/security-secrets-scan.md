# Secrets Scan Validator — .claude/validators/security-secrets-scan.md

Purpose: gate that findings from security skills are complete and that no
secret is echoed in plain text in the findings report itself.

Checks

- Findings report does not contain live credentials/secrets in plain text
- Every finding has a severity, location, and remediation pointer
- Injection/authz/dependency findings are cross-checked against `owasp` categories

Failure handling

- Block the findings report from being shared; redact and re-run
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "security-secrets-scan", "capability": "security"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` when the findings report is persisted.

Usage

Required gate for `injection-scanner`, `dependency-audit`, `authz-check` output
before it is routed back to `backend`/`frontend` for fixes. These skills remain
findings-only; this validator gates the report, not a code change.

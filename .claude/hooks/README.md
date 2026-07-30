# Hooks — .claude/hooks/

Purpose: lightweight, capability-agnostic hooks for lifecycle events. Hooks are
small scripts (prefer Python) that run in a sandboxed manner and receive a
JSON payload via the `HOOK_PAYLOAD` environment variable.

Location

- Place hooks under `.claude/hooks/<event>/` as numbered scripts, e.g.
  `.claude/hooks/pre-run/01-log.py`.

Hook events — implemented

- `pre-run`: before any workflow or skill run
- `post-run`: after successful completion
- `on-validate-fail`: when validators fail
- `on-blueprint-promote`: when a blueprint is promoted
- `on-human-approval-request`: when a human approval is requested
- `on-deploy-failure`: when an automated deploy fails
- `on-artifact-create`: when a new blueprint, playbook or artifact is created
- `on-error`: when an uncaught error occurs
- `pre-commit`: before a git commit finalizes; scans staged files for secrets
- `session-start`: at session start; validates `.claude/` structure and registries

Hook events — documented, not yet implemented (add a folder+script when a real need arises)

- `on-blueprint-demote`, `on-human-approval-response`, `pre-provision`,
  `post-provision`, `on-memory-store`, `on-memory-retrieve`

Runner

Use `tools/run_hook.py <event> '<json-payload>'` to run all scripts registered
for an event, or `tools/run_hook.py <event> --file payload.json` to avoid
shell-quoting issues. The runner sets `HOOK_PAYLOAD` in the environment for
each script.

Windows PowerShell note: passing JSON with double quotes as a single-quoted
argument gets its quotes stripped before reaching the child process. Escape
inner quotes with a backslash, or use `--file`.

Security

- Hooks should not store secrets in plain text.
- Hooks run with the repository user's permissions; treat them as code with
  the same review requirements as other scripts.

Examples

See the sample hooks in this directory for logging, auditing, and notifications.

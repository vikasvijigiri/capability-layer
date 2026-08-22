# Hooks — .claude/hooks/

**Every hook here ACTS or DENIES.** A hook whose only output was the name of a
skill was deleted on 2026-08-04: hooks and skills are independent, a hook cannot
invoke a skill, and a skill name in hook source is an unvalidated copy of a
routing decision. Skills trigger from their own `description:`.

`hooks_registry.json` lists the events and their scripts; `../settings.json` is
the only thing that actually fires them. This file does
not restate either; it says what a hook author needs that is not in those two.

This file is for someone *writing* a hook for Claude Code. Someone *bridging*
these hooks into a different host (Codex, Gemini, VS Code agent) needs
`../../docs/harness-hook-bridge.md` instead — the invocation contract, not the
authoring one.

Until 2026-08-03 this README carried its own event list. It named six events with
no directory on disk (`on-validate-fail`, `on-blueprint-promote`,
`on-human-approval-request`, `on-deploy-failure`, `on-error`, plus a
"not yet implemented" set in a `blueprint`/`provision` vocabulary this repo
dropped long ago), omitted the two that do exist (`pre-edit`, `pre-deploy`), and
described `session-start` as validating registries when it loads knowledge docs.
`test_referenced_paths.py` never caught it because it checks paths, not event
names — a second list is a second thing to keep true, so there is now one.

## Layout

`.claude/hooks/<event>/NN-name.py`, e.g. `permission-security/01-secret-scan.py`. The
number orders scripts within an event; gaps are expected, since nineteen hooks
were deleted on 2026-08-02 and the survivors kept their numbers.

## Writing one

- **Read the payload with `_hooklib.load_payload()`**, never `os.environ`
  directly. Claude Code delivers it on **stdin**; testing by hand sets
  `HOOK_PAYLOAD`. `load_payload` accepts both, so one script works under each.
- **End in `except Exception: pass`.** A hook that raises can wedge a session.
  Every script here does this, and `ruff.toml` silences `S110`/`S112` for the
  directory because of it.
- **Never reorder the imports.** Each script does `sys.path.insert(...)` and
  *then* `from _hooklib import ...`. isort wants to hoist that above the line
  that makes it resolvable, which breaks every hook at once, silently — hence
  `I001` in the same ignore list.
- **Hooks are stateless.** `_hooklib.write_log` was removed on 2026-08-03:
  nothing read any log, Claude Code's own `--debug-file` does it properly, and
  the entries were verbatim prompt text. If you must persist something, write to
  `state/` — gitignored wholesale and excluded by `install.py`.
- **A hook cannot invoke a skill.** It can only *name* one in its output.
- Exit `2` from a `PreToolUse` hook to deny the call. Any other non-zero exit
  lets the action proceed and shows a hook-error notice.

## Testing one

Set the payload in the environment and run the script. There is no runner and
there does not need to be one — `load_payload()` reads `HOOK_PAYLOAD`, so this is
the whole procedure:

    HOOK_PAYLOAD='{}' python .claude/hooks/<event>/<hook>.py
    HOOK_PAYLOAD="$(cat payload.json)" python .claude/hooks/<event>/<hook>.py

A `tools/run_hook.py` wrapper did this until 2026-08-04. It only iterated the
directory and set the variable, and it lived outside `.claude/`, so it went with
the rest of `tools/`.

**A hook bug's symptom is silence, which is identical to "no problem".** A clean
diff proves nothing; fire the script against a realistic payload.

Two traps when you do:

- On Windows, PowerShell strips inner double quotes from a single-quoted argument
  before the child process sees them. Use the Bash tool, or read the payload from
  a file as above.
- **Never fire `stop-finalization/06-artifact-autocommit.py` without
  `UAIOS_AUTOCOMMIT_RUNNING=1`** in the environment. It commits for real
  otherwise, which is the correct behaviour and not what you wanted from a test.

## Security

- Hooks run with the repository user's permissions. They are code, and get the
  same review as code.
- No secrets in plain text. `01-secret-scan.py` and the auto-commit both gate on
  `_hooklib.SECRET_PATTERNS`; the auto-commit checks inline because its own
  commits bypass `PreToolUse` and this hook never sees them.

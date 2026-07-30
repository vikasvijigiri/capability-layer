# Issues

<!-- Append-only, newest entry at the TOP, never rewrite old ones -- same discipline
as LOG.md. One entry per incident (the whole diagnose/fix sequence), written by the
error-recovery skill once a bounded recovery loop reaches a terminal state.
Format: ## YYYY-MM-DD HH:MM -- <short symptom title>, fields per the ISSUES.md section
of knowledge-manager's formats.md. Not preloaded at SessionStart -- consulted on demand. -->

## 2026-07-30 21:10 — `tools/run_hook.py` hangs indefinitely
- **Phase/Context**: After rewriting the hook scripts to read their payload from stdin so
  Claude Code could invoke them directly.
- **Symptom**: `python tools/test_hooks.py` never returned. No error, no output past the
  first event — the process simply sat there until killed.
- **Diagnosis**: `run_hook.py` spawns each hook with `subprocess.run([...], env=env)` and
  no `stdin` argument, so the child inherits the parent's stdin. When the parent was
  itself launched from a pipe, that handle never reaches EOF, and `sys.stdin.read()`
  blocks forever. The `isatty()` guard does not help: an inherited pipe is not a TTY, so
  the check passes and the read still blocks.
- **Attempts**:
  - 1. Ran the same suite earlier and it passed → misleading; stdin happened to be at EOF
    in that context, so the bug was invisible rather than absent.
  - 2. Reordered `_hooklib.load_payload()` to read `HOOK_PAYLOAD` before stdin → fixed.
- **Fix**: `load_payload()` checks the env var first. `run_hook.py` always sets it, so the
  only caller that leaves stdin dangling never reaches the stdin branch. Claude Code sets
  no `HOOK_PAYLOAD` and always writes real JSON to stdin, so it falls through correctly.
  The ordering is documented in the function as load-bearing.
- **Status**: `Resolved`

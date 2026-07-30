# Register hook scripts directly, with no dispatcher

## Decision

Each script under `.claude/hooks/<event>/` is registered individually in
`.claude/settings.json` against the Claude Code lifecycle event it belongs to, and
decides for itself whether a given payload is relevant. There is no dispatcher,
router or adapter process in between.

The one shared piece is `_hooklib.load_payload()`, which accepts a payload from
either stdin (Claude Code) or `HOOK_PAYLOAD` (`tools/run_hook.py`). That dual
input is what lets direct registration coexist with the validator-invoked path
CLAUDE.md requires.

`on-blueprint-promote` stays unregistered — promoting a blueprint is a domain
action, not a moment in a session, so no lifecycle event corresponds to it.

## Why

The two hook systems disagree on payload transport, event names, decision
signalling and working directory, so a bridge was the obvious first move and was
in fact built (`tools/cc_hook_adapter.py`). It worked, and was still wrong:

- It became a second place where routing lived. Knowing when `on-validate-fail`
  fires meant reading the adapter, not the hook — the file named after the
  behaviour was the one that did not describe it.
- It diverged from `~/.claude/hooks/`, where every script is self-contained and
  self-filtering. One repo behaving differently from the global layer is a tax on
  everyone who reads either.
- A dispatcher fails as a unit. A bug in it silently disables every hook at once,
  which is the worst possible blast radius for a component whose entire job is to
  be a safety net.

Self-filtering costs a few lines per script and matches how the global hooks
already work: `review_gate.py` owns its own `COMMIT_RE` rather than trusting the
settings matcher alone.

## Alternatives considered

- **Keep the adapter.** One process per event instead of N, which is a real
  saving on `PostToolUseFailure` (3 scripts → 3 interpreter starts). Rejected:
  the cost is milliseconds on an already-failed tool call, and it buys back the
  indirection this decision exists to remove.
- **Rely on settings `matcher` alone and drop in-script checks.** Rejected: a
  matcher narrows by tool name, not by command shape. `pre-commit` must
  distinguish `git commit` from `git commit --dry-run` from `git status`, none of
  which a tool-name matcher can see.
- **Rewrite the hooks to abandon `run_hook.py` entirely.** Rejected: CLAUDE.md
  requires validators to invoke `on-validate-fail`/`on-artifact-create` directly,
  and a validator knows its own result in a way no lifecycle event can observe.

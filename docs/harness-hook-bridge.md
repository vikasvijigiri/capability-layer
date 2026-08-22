# Harness hook bridge

What a non-Claude-Code host must do to run this layer's hooks. Claude Code
discovers and fires `.claude/hooks/` natively via `.claude/settings.json`; a
host without that discovery mechanism (Codex, Gemini, a VS Code agent, or
anything else `harnesses.json` names) must call the same scripts itself. This
is the contract for doing that correctly.

Before wiring a bridge, read `.claude/portability/capabilities.json` and the
host's manifest under `.claude/adapters/`. A safety-critical capability marked
`bridge-required` is not available until its named conformance check exists and
passes. The host must refuse the dependent irreversible action rather than
pretend its own permission prompt is equivalent.

`.claude/hooks/hooks_registry.json` is the source of truth for *which* events
exist and *which* scripts subscribe to each — this file is not a second copy
of that list. It documents the invocation mechanics `hooks_registry.json`
doesn't state.

## The moments

Each key in `hooks_registry.json["events"]` is a lifecycle moment, not a
Claude-Code-specific concept: a session starting, a turn about to begin, a
turn having completed, a commit about to finalize, a file about to be written,
a cloud-spend command about to run, a hook script having just been edited. A
host maps its own lifecycle to these moments and fires the listed scripts at
the matching point, in the listed order.

`hooks_registry.json`'s `claude_code_event` field per entry names Claude
Code's own event so the mapping to Anthropic's documented hook payload shape
for that event is unambiguous — construct the payload as Claude Code would for
that event, not a bespoke shape.

## Payload delivery

Every script reads its payload through `_hooklib.load_payload()`, which
accepts either:

- **stdin** — a single JSON object, written and closed before the script
  reads it (Claude Code's own delivery mechanism); or
- **the `HOOK_PAYLOAD` environment variable** — the same JSON object as a
  string.

A bridging host may use whichever is more natural to its own process-spawning
API. No third delivery path exists and none should be added — introducing one
would mean every hook script starts caring which host invoked it, which
`_hooklib`'s docstring calls out as the thing this design avoids.

## Exit-code contract

- **Events wired to `PreToolUse`** in `hooks_registry.json`
  (`permission-security`, `pre-edit`, `pre-tool`) — exit `2` means deny: the
  host must not perform the action the hook was asked about. Any other
  non-zero exit means allow, with a hook-error notice surfaced to the
  operator; exit `0` means allow, silently.
- **Every other event** (`session-init`, `prompt-intake`, `stop-finalization`,
  `telemetry`, `post-edit-validation`) is not a gate. These hooks detect
  drift, render state, or checkpoint; their exit code is not read as
  allow/deny by Claude Code and a bridging host must not treat it as one
  either. Stdout is the report.

## Ordering and independence

Run a given event's subscriber list in the order `hooks_registry.json` lists
it — some scripts checkpoint state a later one in the same event reads. Across
different events there is no ordering requirement. A hook never invokes
another hook or a skill; it only acts, denies, or reports, so a bridging host
does not need to resolve any hook-to-hook dependency graph beyond the one
list.

## Verifying a bridge

Prove the bridge against a real payload before trusting it, the same
standard `.claude/hooks/README.md` sets for a native Claude Code hook:

```sh
HOOK_PAYLOAD='{}' python .claude/hooks/<event>/<script>.py
```

Confirm the exit code and stdout match what the contract above predicts for
that payload. A hook bug's symptom is silence — identical to "no problem" —
so a bridge that has never been fired against a real payload is unverified,
not working.

## What this does not cover

There is no standalone repository runner today — see `AGENTS.md`'s Runtime
model section. This document describes how an interactive IDE-style host
bridges the hook layer; it does not describe unattended automation, which
would need its own contract if built.

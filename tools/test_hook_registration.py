#!/usr/bin/env python3
"""Tests that disk, settings.json and hooks_registry.json agree about hooks.

Why this suite exists
---------------------
`/verify` step 4 has described this exact check in prose since the command was
written, and the drift it describes accumulated anyway:

- `session-start/02-bootstrap-docs.py` was in the registry, on disk, and NOT in
  `settings.json` — so the hook that injects the knowledge docs into session
  context **never fired in a real session**. CLAUDE.md's "six files carry state
  between sessions" was describing a capability that was not wired.
- `post-run/05-docs-gate.py` and `pre-commit/05-docs-required.py` were wired and
  on disk but absent from the registry, so the file documenting intent disagreed
  with the file that fires.

A check a human is asked to run by hand is a check that eventually is not run.
Three directions are asserted here, because a hook can be invisible in three
different ways and each is silent:

1. On disk but not in settings.json  -> never fires.
2. In settings.json but not on disk  -> fires and errors, or silently no-ops.
3. On disk but not in the registry   -> fires, but nothing documents why.

Run: python tools/test_hook_registration.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"
REGISTRY = HOOKS / "hooks_registry.json"

# Directories under .claude/hooks/ that hold no hook scripts.
NON_EVENT_DIRS = {"state", "__pycache__"}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def rel(path: str) -> str:
    """Normalise any way a hook path is written down to `<event>/<script>.py`."""
    path = path.replace("\\", "/").rstrip('"')
    marker = ".claude/hooks/"
    if marker in path:
        path = path.split(marker, 1)[1]
    return path.strip('" ')


# --- gather the three views -------------------------------------------------

on_disk = {
    f"{d.name}/{f.name}"
    for d in HOOKS.iterdir()
    if d.is_dir() and d.name not in NON_EVENT_DIRS
    for f in d.iterdir()
    if f.suffix == ".py"
}

settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
wired: set[str] = set()
for blocks in settings.get("hooks", {}).values():
    for block in blocks:
        for hook in block.get("hooks", []):
            cmd = hook.get("command", "")
            if ".claude/hooks/" in cmd:
                wired.add(rel(cmd.split()[-1] if " " in cmd else cmd))

registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["events"]
declared = {rel(s) for e in registry.values() for s in e["subscribers"]}

# Events with no `claude_code_event` have no lifecycle trigger and are fired by
# hand through tools/run_hook.py. Their scripts are exempt from direction 1.
manual_only = {
    rel(s)
    for e in registry.values()
    if not e.get("claude_code_event")
    for s in e["subscribers"]
}

print(f"{len(on_disk)} scripts on disk, {len(wired)} wired, {len(declared)} declared")
print()

# --- direction 1: on disk, not wired ---------------------------------------

unwired = sorted(on_disk - wired - manual_only)
check("every hook on disk is wired in settings.json", not unwired,
      f"never fires: {', '.join(unwired)}")

# --- direction 2: wired, not on disk ---------------------------------------

phantom = sorted(wired - on_disk)
check("every hook wired in settings.json exists on disk", not phantom,
      f"registered but missing: {', '.join(phantom)}")

# --- direction 3: on disk, not declared ------------------------------------

undocumented = sorted(on_disk - declared)
check("every hook on disk is declared in hooks_registry.json", not undocumented,
      f"undocumented: {', '.join(undocumented)}")

stale = sorted(declared - on_disk)
check("every hook declared in hooks_registry.json exists on disk", not stale,
      f"declared but missing: {', '.join(stale)}")

# --- every event directory is a registry event ------------------------------

event_dirs = {d.name for d in HOOKS.iterdir()
              if d.is_dir() and d.name not in NON_EVENT_DIRS}
unregistered_dirs = sorted(event_dirs - set(registry))
check("every hook event directory has a registry entry", not unregistered_dirs,
      f"no entry: {', '.join(unregistered_dirs)}")

empty_events = sorted(k for k, v in registry.items() if not v.get("subscribers"))
check("no registry event has an empty subscriber list", not empty_events,
      f"empty: {', '.join(empty_events)}")

# --- direction 5: reject stale global registrations --------------------------
#
# This repository intentionally ships no global hook. A user-level settings file
# must therefore not point at a deleted repository path.

STALE_GLOBAL = {"global-session-start/01-layer-bootstrap.py"}

global_settings = Path.home() / ".claude" / "settings.json"
if not global_settings.is_file():
    print(f"SKIP: no {global_settings} -- external stale-hook check unavailable")
else:
    try:
        gs = json.loads(global_settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        gs = {}
        check("~/.claude/settings.json parses", False, str(exc))
    global_wired = {
        rel(hook.get("command", "").split()[-1])
        for blocks in gs.get("hooks", {}).values()
        for block in blocks
        for hook in block.get("hooks", [])
        if ".claude/hooks/" in hook.get("command", "")
    }
    stale_global = sorted(STALE_GLOBAL & global_wired)
    check("external settings contain no stale repository hooks", not stale_global,
          ", ".join(stale_global) if stale_global else "clean")

# --- no hook may name a skill in anything it emits --------------------------
#
# Hooks measure and act; deciding which skill owns a fact is routing, and
# `.claude/workflow.md` owns that. A skill name inside hook source is an
# unvalidated second copy of that decision: three hooks carried one until
# 2026-08-04, and pointing one at a fabricated skill passed every suite in the
# repo. Those hooks are gone; this is what stops them coming back.
#
# Only EMITTED strings are checked, parsed out of the AST. Docstrings and
# comments may still explain history -- they never reach a session.

import ast  # noqa: E402, PLC0415

SKILL_NAMES = {d.name for d in (ROOT / ".claude" / "skills").iterdir() if d.is_dir()}

for _path in sorted(HOOKS.rglob("*.py")):
    if "__pycache__" in _path.parts or _path.name.startswith("_"):
        continue
    try:
        tree = ast.parse(_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        check(f"{_path.name} parses", False, str(exc)[:80])
        continue
    doc = ast.get_docstring(tree) or ""
    emitted = [n.value for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and n.value != doc and len(n.value) < 4000]
    named = sorted({s for s in SKILL_NAMES if any(s in e for e in emitted)})
    check(f"{_path.parent.name}/{_path.name} names no skill in what it emits",
          not named, f"names {named} -- workflow.md decides, the hook measures")

# --- every state the report hook can emit has a workflow.md block -----------
#
# The hook renders `[state:<key>]` blocks out of workflow.md and deliberately
# keeps no fallback text, so a key with no block degrades to a generic line. That
# is the right failure, but it should not be discovered in a live session.
#
# An unclosed tag is worse: the regex simply does not match, so the block is
# present, looks correct, and is never emitted.

_report = HOOKS / "session-start" / "03-state-report.py"
_wf = ROOT / ".claude" / "workflow.md"
if _report.is_file() and _wf.is_file():
    _src = _report.read_text(encoding="utf-8")
    _wf_text = _wf.read_text(encoding="utf-8")
    # The keys the hook can append, read from its own source rather than repeated
    # here -- a list in this file would be the second copy the whole design avoids.
    _keys = set(re.findall(r'states\.append\("([a-z-]+)"\)', _src))
    check("the report hook declares at least one state", bool(_keys))
    for _key in sorted(_keys):
        check(f"workflow.md has a closed [state:{_key}] block",
              f"[state:{_key}]" in _wf_text and f"[/state:{_key}]" in _wf_text,
              "missing or unclosed -- an unclosed tag never matches and is silent")

# --- every SessionStart hook survives being invoked, for every source -------
#
# SessionStart hooks run before anyone can see a prompt, so a crash there is the
# most invisible failure the layer has: the session opens, the context is simply
# missing, and nothing says why. Directions 1-3 above prove the wiring exists;
# this proves the wired thing RUNS.
#
# Invoked through the command string in settings.json rather than a path written
# here, so a broken registration is caught too. `source` is exercised across all
# three values Claude Code sends -- `compact` and `resume` are the branches that
# only execute after a context boundary, which is exactly when nobody is watching.
#
# What this cannot prove: that Claude Code actually invokes them, or that it acts
# on `reloadSkills`. Both need a real session. Recorded in HANDOFF.md as such.

# **Run as a subprocess, exit code asserted, is a check that cannot fail.** That
# was the first version and a planted `raise` in a hook passed it: every hook here
# ends in `except Exception: sys.exit(0)` so a crash never reaches the shell. The
# fail-open guard is correct in production and it makes the exit code carry no
# information at all in a test.
#
# So `main()` is called IN-PROCESS, inside the guard, where an exception is still
# an exception. stdout is captured the same way the harness reads it.

import importlib.util  # noqa: E402, PLC0415
import io  # noqa: E402, PLC0415
import os  # noqa: E402, PLC0415
from contextlib import redirect_stdout  # noqa: E402, PLC0415


def _load_hook(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"no loader for {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_ss_blocks = settings.get("hooks", {}).get("SessionStart", [])
_cmds = [h.get("command", "") for _b in _ss_blocks for h in _b.get("hooks", [])]
check("SessionStart has at least one registered hook", bool(_cmds))
for _i, _cmd in enumerate(_cmds):
    _script = _cmd.replace("$CLAUDE_PROJECT_DIR", str(ROOT)).replace('"', '')
    _script = _script.split(None, 1)[1] if " " in _script else _script
    _path = Path(_script)
    _name = _path.name
    if not _path.is_file():
        check(f"{_name} exists to be invoked", False, "registered but not on disk")
        continue
    try:
        _mod = _load_hook(_path, f"_ss_hook_{_i}")
    except Exception as _exc:  # noqa: BLE001 - import failure IS the finding
        check(f"{_name} imports", False, f"{type(_exc).__name__}: {_exc}"[:110])
        continue
    for _source in ("startup", "resume", "compact"):
        os.environ["HOOK_PAYLOAD"] = json.dumps({"source": _source})
        os.environ["UAIOS_AUTOCOMMIT_RUNNING"] = "1"
        _buf = io.StringIO()
        _raised = ""
        try:
            with redirect_stdout(_buf):
                _mod.main()
        except Exception as _exc:  # noqa: BLE001 - a raise is the finding
            _raised = f"{type(_exc).__name__}: {_exc}"
        check(f"{_name} runs clean on source={_source}", not _raised, _raised[:110])
        # Silence is legal; malformed JSON is not -- the harness discards the whole
        # payload and the hook looks like it ran.
        _out = _buf.getvalue().strip()
        if not _raised and _out:
            try:
                _d = json.loads(_out)["hookSpecificOutput"]
                check(f"{_name} declares hookEventName on source={_source}",
                      _d.get("hookEventName") == "SessionStart",
                      f"got {_d.get('hookEventName')!r}")
            except (ValueError, KeyError) as _exc:
                check(f"{_name} emits valid hook JSON on source={_source}",
                      False, str(_exc)[:100])
os.environ.pop("HOOK_PAYLOAD", None)

# --- the manual-only exemption must be deliberate, not a typo ---------------

for name, entry in sorted(registry.items()):
    if entry.get("claude_code_event"):
        continue
    check(f"manual-only event '{name}' says why it is unwired",
          bool(entry.get("_note")),
          "no _note explaining the absent claude_code_event")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All hook-registration tests passed ({len(on_disk)} hooks, "
      f"{len(event_dirs)} events)")

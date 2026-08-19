#!/usr/bin/env python3
"""Tests for tools/halt.py and .claude/hooks/pre-run/01-halt-guard.py.

Three things this suite has to prove, because a kill switch that fails any one
of them is worse than none:

  1. `halt()` / `status()` / `resume()` behave correctly as pure state on one
     flag file under `.claude/hooks/state/` (gitignored, machine-local).
  2. The guard hook, fired for real with `HOOK_PAYLOAD` -- not imported and
     asserted against in-process -- denies while halted and is silent
     otherwise. A hook bug's symptom is silence, so importing the function and
     calling it directly would not catch a broken `sys.path` shim or a crash
     that only happens under the real subprocess entry point.
  3. Halting and resuming take no destructive action: the tracked working
     tree hashes identically before halt, after halt, and after resume.

Run: python tools/test_halt.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".claude" / "hooks" / "pre-run" / "01-halt-guard.py"
STATE_DIR = ROOT / ".claude" / "hooks" / "state"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None, f"no import spec for {rel}"
    assert spec.loader is not None, f"no loader for {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


halt_mod = load("tools/halt.py", "halt_mod")


def tree_hash() -> str:
    """A hash of every tracked file's content, in path order.

    Deliberately over the git-tracked set (`git ls-files`), not a raw
    filesystem walk: the halt flag itself lives under `.claude/hooks/state/`,
    which is gitignored, so a raw walk would see it change and call that a
    tree difference when it is exactly the file this mechanism is allowed to
    touch. What must not move is the tracked tree.
    """
    proc = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
        timeout=15, shell=False,
    )
    assert proc.returncode == 0, f"git ls-files failed: {proc.stderr}"
    paths = sorted(p for p in proc.stdout.splitlines() if p.strip())
    digest = hashlib.sha256()
    for rel in paths:
        p = ROOT / rel
        digest.update(rel.encode("utf-8"))
        try:
            digest.update(p.read_bytes())
        except OSError:
            digest.update(b"<unreadable>")
    return digest.hexdigest()


def fire_guard(payload: str = "{}") -> tuple[str, float]:
    """Run the real hook entry point as a subprocess, the way Claude Code and
    tools/run_hook.py both do -- never by importing and calling a function."""
    import os
    env = os.environ.copy()
    env["HOOK_PAYLOAD"] = payload
    env["PYTHONIOENCODING"] = "utf-8"
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(GUARD)], env=env, capture_output=True, text=True,
        timeout=30,
    )
    elapsed = time.monotonic() - start
    return proc.stdout.strip(), elapsed


def cleanup():
    halt_mod.resume()


# --- always start clean, and always end clean -------------------------------
cleanup()

try:
    # --- pure state: halt / status / resume ---------------------------------

    check("not halted before anything happens",
          halt_mod.status() == {"halted": False})

    record = halt_mod.halt("smoke test reason")
    check("halt() reports the reason back", record["reason"] == "smoke test reason")

    st = halt_mod.status()
    check("status() reports halted with the same reason",
          st["halted"] is True and st["reason"] == "smoke test reason", str(st))

    resumed = halt_mod.resume()
    check("resume() reports it lifted a real halt", resumed is True)
    check("status() is clear after resume", halt_mod.status() == {"halted": False})

    resumed_again = halt_mod.resume()
    check("resuming when not halted reports nothing to lift",
          resumed_again is False)

    # halting twice keeps the original `since` timestamp
    halt_mod.halt("first reason")
    first_since = halt_mod.status()["since"]
    time.sleep(0.05)
    halt_mod.halt("second reason")
    second = halt_mod.status()
    check("a second halt call keeps the original since timestamp",
          second["since"] == first_since, str(second))
    check("a second halt call updates the reason",
          second["reason"] == "second reason")
    halt_mod.resume()

    # a corrupt flag file is treated as halted, not as a crash
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "halt.json").write_text("not json", encoding="utf-8")
    corrupt_status = halt_mod.status()
    check("a corrupt flag reports halted rather than raising",
          corrupt_status["halted"] is True, str(corrupt_status))
    halt_mod.resume()

    # --- the guard hook, fired for real --------------------------------------

    out_clear, elapsed_clear = fire_guard()
    check("guard is silent when not halted", out_clear == "", repr(out_clear))
    check("guard runs fast when not halted (< 2s)", elapsed_clear < 2.0,
          f"{elapsed_clear:.2f}s")

    halt_mod.halt("guard smoke test")
    out_halted, elapsed_halted = fire_guard()
    check("guard runs fast while halted (< 2s)", elapsed_halted < 2.0,
          f"{elapsed_halted:.2f}s")

    try:
        parsed = json.loads(out_halted)
        deny_ok = (
            parsed.get("hookSpecificOutput", {}).get("permissionDecision")
            == "deny"
        )
    except (ValueError, AttributeError):
        deny_ok = False
    check("guard denies while halted", deny_ok, out_halted)
    check("denial names how to resume",
          "tools/halt.py --resume" in out_halted, out_halted)
    check("denial names no skill (only a tool)",
          not any(term in out_halted.lower()
                  for term in ("writing-plans", "executing-plans", "code-review",
                               "no-slop", "releasing", "delivering",
                               "brainstormer", "systematic-debugging")),
          out_halted)

    halt_mod.resume()
    out_after_resume, _ = fire_guard()
    check("guard is silent again after resume", out_after_resume == "",
          repr(out_after_resume))

    # --- must not strand work: byte-identical tree across halt/resume -------

    before = tree_hash()
    halt_mod.halt("tree-identity check")
    during = tree_hash()
    halt_mod.resume()
    after = tree_hash()

    check("tracked tree is unchanged by halting", during == before)
    check("tracked tree is unchanged by resuming", after == before)

finally:
    cleanup()

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All halt tests passed")

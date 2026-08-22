#!/usr/bin/env python3
"""Tests for `.claude/hooks/context-budget/01-context-cost.py`.

This hook had zero test coverage until this file (confirmed: no
`test_context_cost*` existed anywhere in the repo before the 2026-08-22
run_id/VOLATILE-cd-prefix unit). The regression this file exists to prove:
every real command in this environment is wrapped `cd "<dir>" && <command>`,
which defeated `VOLATILE`'s `startswith()` check entirely -- a legitimately
exempt re-run (`git status`, `tools/resume.py`, ...) was being counted as a
wasteful repeat purely because of the wrapper, inflating the reported
duplicate-call rate with false positives.

Run: python tools/test_context_cost.py
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = load(".claude/hooks/context-budget/01-context-cost.py", "cc_for_test")

# Point STATE at a throwaway file for the whole run -- repeat_notice() reads
# and writes real state, and this must never touch the live
# call-fingerprints.json (gitignored, per-machine, real session data).
_fd, _tmp_state_path = tempfile.mkstemp(suffix=".json")
os.close(_fd)
_ORIGINAL_STATE = cc.STATE
cc.STATE = Path(_tmp_state_path)

# --- _strip_cd_prefix() -------------------------------------------------------

check("_strip_cd_prefix: strips a double-quoted cd path before &&",
      cc._strip_cd_prefix('cd "c:/Users/x/y" && git status --porcelain')
      == "git status --porcelain")
check("_strip_cd_prefix: strips a single-quoted cd path before ;",
      cc._strip_cd_prefix("cd '/tmp/x'; ls") == "ls")
check("_strip_cd_prefix: strips an unquoted cd path",
      cc._strip_cd_prefix("cd /tmp && ls") == "ls")
check("_strip_cd_prefix: a command with no cd prefix is unchanged",
      cc._strip_cd_prefix("git status --porcelain") == "git status --porcelain")

# --- repeat_notice(): the regression case -------------------------------------
#
# THE SPECIFIC BUG: a cd-wrapped VOLATILE command must be exempt from the
# repeat notice on its second call. Before the fix, VOLATILE's startswith()
# checked the wrapped string directly and never matched, so this exact case
# incorrectly produced a [repeat] notice.
_cmd_volatile = 'cd "/tmp/x" && git status --porcelain'
cc.repeat_notice("Bash", _cmd_volatile)  # first call: seeds state
_notice_second = cc.repeat_notice("Bash", _cmd_volatile)  # second call
check("repeat_notice: a cd-wrapped VOLATILE command (git status) produces NO "
      "notice on its second call -- the exact regression this fix closes",
      _notice_second == "",
      f"got notice: {_notice_second!r}")

# --- repeat_notice(): the fix must not exempt everything ----------------------
#
# A cd-wrapped NON-volatile command repeated verbatim must still notice --
# proving the fix narrows the false positive without disabling real detection.
_cmd_real = 'cd "/tmp/x" && echo a genuinely novel non-volatile probe command'
cc.repeat_notice("Bash", _cmd_real)
_notice_real = cc.repeat_notice("Bash", _cmd_real)
check("repeat_notice: a cd-wrapped NON-volatile repeated command DOES still "
      "produce a [repeat] notice -- the fix did not exempt everything",
      _notice_real.startswith("[repeat]"),
      f"got: {_notice_real!r}")

# --- MIN_REPEAT_CHARS: measured against the de-prefixed command --------------
#
# A trivial command (e.g. "ls", 2 chars) must not clear the length floor
# purely because its cd wrapper is long -- confirms the floor is measured
# against check_target, not the raw wrapped command.
_cmd_trivial = 'cd "c:/a/very/long/directory/path/that/is/definitely/over/forty/chars" && ls'
assert len(_cmd_trivial) >= cc.MIN_REPEAT_CHARS, "test setup: wrapper must be long"
cc.repeat_notice("Bash", _cmd_trivial)
_notice_trivial = cc.repeat_notice("Bash", _cmd_trivial)
check("repeat_notice: a trivial de-prefixed command (ls) stays below "
      "MIN_REPEAT_CHARS even with a long cd wrapper -- no notice either call",
      _notice_trivial == "",
      f"got: {_notice_trivial!r}")

cc.STATE = _ORIGINAL_STATE
Path(_tmp_state_path).unlink(missing_ok=True)

if failures:
    print(f"\n{len(failures)} failed: " + "; ".join(failures))
    raise SystemExit(1)
print("\nAll context-cost tests passed")

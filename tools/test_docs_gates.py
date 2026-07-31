#!/usr/bin/env python3
"""Tests for the two docs gates: post-run/05-docs-gate.py and pre-commit/05-docs-required.py.

Both were verified by ad-hoc inline runs when written and neither had a committed
test. That is the gap this closes. The sibling hook in this family
(`pre-run/04-docs-staleness.py`) shipped two bugs, both in branch logic, both of
which presented as *silence* -- and silence is also what "no problem" looks like.
Gates fail the same way: one that never fires is indistinguishable from one with
nothing to report.

Git output is injected rather than read, so every branch runs without needing the
repo in that state.

Run: python tools/test_docs_gates.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def emit(mod) -> dict:
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.main()
    out = buf.getvalue().strip()
    return json.loads(out) if out else {}


WORK = [f"src/f{i}.py" for i in range(12)]

# ---------------------------------------------------------------- Stop gate
gate = load(".claude/hooks/post-run/05-docs-gate.py", "docs_gate")

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    gate.REPO_ROOT = tmp
    now = time.time()
    for rel in WORK:
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        os.utime(p, (now, now))

    def docs(newer: bool) -> None:
        for doc in ("LOG.md", "HANDOFF.md"):
            p = tmp / doc
            p.write_text("x", encoding="utf-8")
            stamp = now + 10 if newer else now - 10
            os.utime(p, (stamp, stamp))

    gate.changed_files = lambda: WORK
    gate.load_payload = lambda: {"stop_hook_active": False}
    docs(False)
    check("stop gate blocks when docs are behind", emit(gate).get("decision") == "block")

    docs(True)
    check("stop gate silent when docs are current", emit(gate) == {})

    docs(False)
    gate.load_payload = lambda: {"stop_hook_active": True}
    check("stop gate honours stop_hook_active (cannot loop)", emit(gate) == {})

    gate.load_payload = lambda: {}
    check("stop gate tolerates a payload with no stop_hook_active key",
          emit(gate).get("decision") == "block")

    gate.changed_files = lambda: WORK[:5]
    check("stop gate silent below MIN_FILES", emit(gate) == {})

    gate.changed_files = lambda: None
    check("stop gate fails open when git cannot answer", emit(gate) == {})

# ------------------------------------------------------- pre-commit gate
req = load(".claude/hooks/pre-commit/05-docs-required.py", "docs_required")

for cmd, expected in [
    ("git commit -m x", True), ("git -C /r commit", True),
    ("git -c user.name=x commit", True), ("cd /x && git commit -q", True),
    ("/usr/bin/git commit", True), ("git commit-tree abc", False),
    ("git status", False), ("git log --format=commit", False),
    ("echo commit", False), ("git add -A", False),
]:
    check(f"detects {cmd!r} as commit={expected}", req.is_git_commit(cmd) == expected)


def run_req(staged, cmd="git commit -m x", override=None) -> dict:
    req.staged_files = lambda: staged
    req.load_payload = lambda: {"tool_input": {"command": cmd}}
    prev = os.environ.pop("ALLOW_UNLOGGED_COMMIT", None)
    if override:
        os.environ["ALLOW_UNLOGGED_COMMIT"] = override
    try:
        return emit(req)
    finally:
        os.environ.pop("ALLOW_UNLOGGED_COMMIT", None)
        if prev:
            os.environ["ALLOW_UNLOGGED_COMMIT"] = prev


def denied(result: dict) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


check("commit gate denies an unlogged commit", denied(run_req(WORK)))
check("commit gate allows when LOG.md is staged", not denied(run_req(WORK + ["LOG.md"])))
check("commit gate allows when HANDOFF.md is staged",
      not denied(run_req(WORK + ["HANDOFF.md"])))
check("commit gate allows below MIN_FILES", not denied(run_req(WORK[:5])))
check("commit gate ignores non-commit commands", not denied(run_req(WORK, "git status")))
check("commit gate honours ALLOW_UNLOGGED_COMMIT", not denied(run_req(WORK, override="1")))
check("commit gate fails open when git cannot answer", not denied(run_req(None)))

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All docs-gate tests passed")

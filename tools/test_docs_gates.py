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

    # The gate compares doc CONTENT against a snapshot taken at UserPromptSubmit,
    # not mtimes. It used to compare mtimes, which false-blocked three times on
    # 2026-08-01 with the docs correctly written -- git's index refresh bumps
    # working-file mtimes, and an uncommitted backlog keeps old ones forever.
    # These cases pin the content semantics, including that mtime is now irrelevant.
    snapshot = {}

    def write_docs(log_body: str, handoff_body: str) -> None:
        (tmp / "LOG.md").write_text(log_body, encoding="utf-8")
        (tmp / "HANDOFF.md").write_text(handoff_body, encoding="utf-8")

    gate.changed_files = lambda: WORK
    gate.load_payload = lambda: {"stop_hook_active": False}
    gate.doc_digests = lambda: {d: (tmp / d).read_text(encoding="utf-8")
                                for d in ("LOG.md", "HANDOFF.md")}
    gate.load_turn_marker = lambda: snapshot or None

    write_docs("before", "before")
    snapshot = {"LOG.md": "before", "HANDOFF.md": "before"}
    check("stop gate blocks when neither doc was written this turn",
          emit(gate).get("decision") == "block")

    write_docs("AFTER", "before")
    check("stop gate silent when LOG.md was written this turn", emit(gate) == {})

    write_docs("before", "AFTER")
    check("stop gate silent when HANDOFF.md was written this turn", emit(gate) == {})

    # The regression that motivated the rewrite: correct content, ancient mtime.
    write_docs("AFTER", "AFTER")
    for doc in ("LOG.md", "HANDOFF.md"):
        os.utime(tmp / doc, (0, 0))
    check("stop gate ignores mtime -- silent on written docs with a 1970 mtime",
          emit(gate) == {})

    # ...and the inverse: fresh mtime must not excuse unwritten content.
    write_docs("before", "before")
    for doc in ("LOG.md", "HANDOFF.md"):
        os.utime(tmp / doc, (now + 9999, now + 9999))
    check("stop gate ignores mtime -- blocks on unwritten docs with a future mtime",
          emit(gate).get("decision") == "block")

    # The trigger must be per-turn, not standing. The gate's `work` set is the whole
    # uncommitted backlog, so once it passes MIN_FILES every later turn tripped the
    # gate -- including turns that changed nothing -- because the doc check is
    # per-turn while the trigger was not. Five blocks in one session on 2026-08-02,
    # three of them talked past with the gate's own escape hatch. The marker now
    # carries the turn-start work set so "this turn added nothing" is answerable.
    write_docs("before", "before")
    snapshot = {"LOG.md": "before", "HANDOFF.md": "before", "work": sorted(WORK)}
    check("stop gate silent when this turn added no work", emit(gate) == {})

    snapshot = {"LOG.md": "before", "HANDOFF.md": "before", "work": sorted(WORK[:11])}
    check("stop gate blocks when this turn added work and docs are unwritten",
          emit(gate).get("decision") == "block")

    reason = emit(gate).get("reason", "")
    check("block reason does not claim an mtime comparison it no longer performs",
          "older than" not in reason, f"reason was: {reason[:80]}")

    snapshot = {"LOG.md": "before", "HANDOFF.md": "before"}
    check("stop gate still blocks on a legacy marker with no work key",
          emit(gate).get("decision") == "block")

    snapshot = {"LOG.md": "before", "HANDOFF.md": "before", "work": None}
    check("stop gate blocks when the turn-start work set was unknowable",
          emit(gate).get("decision") == "block")

    snapshot = {}
    check("stop gate allows when no snapshot exists (first turn)", emit(gate) == {})

    # Back to the blocking condition -- unwritten docs and a live snapshot -- so the
    # cases below exercise their own guard rather than riding on an allow.
    write_docs("before", "before")
    snapshot = {"LOG.md": "before", "HANDOFF.md": "before"}

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

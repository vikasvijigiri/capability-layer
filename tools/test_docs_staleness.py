#!/usr/bin/env python3
"""Tests for pre-run/04-docs-staleness.py.

This hook has shipped two bugs, both in branch logic, both of which looked like
a pass because the hook was *silent* -- and silence is what "no problem" looks
like too:

1. It asked "is LOG.md among the changed files?", so once LOG.md was edited and
   left uncommitted it stayed in the changed set and the hook went quiet for the
   rest of the session, exactly while work piled up.
2. It returned early on a clean tree, so committing work *without* logging it
   silenced the hook permanently -- the staleness baked into history, invisible.

Both were found by eye, not by a check. Hence this file: git output is injected
rather than read, so every branch is exercised without needing a repo in that
state.

Run: python tools/test_docs_staleness.py
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
HOOK = ROOT / ".claude" / "hooks" / "pre-run" / "04-docs-staleness.py"

spec = importlib.util.spec_from_file_location("docs_staleness", HOOK)
mod = importlib.util.module_from_spec(spec)
sys.modules["docs_staleness"] = mod
spec.loader.exec_module(mod)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def run(changed, head, doc_mtime_newer: bool, tmp: Path) -> str:
    """Invoke main() with git output injected; returns injected context or ''."""
    mod.changed_files = lambda: changed
    mod.head_files = lambda: head
    mod.REPO_ROOT = tmp

    now = time.time()
    for rel in set((changed or []) + (head or [])):
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        os.utime(p, (now, now))
    for doc in ("LOG.md", "HANDOFF.md"):
        p = tmp / doc
        p.write_text("x", encoding="utf-8")
        stamp = now + 10 if doc_mtime_newer else now - 10
        os.utime(p, (stamp, stamp))

    mod.load_payload = lambda: {"prompt": "carry on"}
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.main()
    out = buf.getvalue().strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""


WORK = ["src/a.py", "src/b.py", "src/c.py", "src/d.py"]

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)

    # --- uncommitted-work branch ---
    ctx = run(WORK, [], doc_mtime_newer=False, tmp=tmp)
    check("fires when uncommitted work is newer than the docs",
          "uncommitted" in ctx, f"got: {ctx[:80]!r}")

    ctx = run(WORK, [], doc_mtime_newer=True, tmp=tmp)
    check("silent when the docs are newer than the work", ctx == "", f"got: {ctx[:80]!r}")

    # Regression for bug 1: LOG.md present in the changed set must NOT buy silence.
    ctx = run(WORK + ["LOG.md", "HANDOFF.md"], [], doc_mtime_newer=False, tmp=tmp)
    check("edited-but-stale docs still fire (bug 1 regression)",
          "uncommitted" in ctx, f"got: {ctx[:80]!r}")

    # --- clean-tree branch (bug 2) ---
    ctx = run([], WORK, doc_mtime_newer=True, tmp=tmp)
    check("fires when the last commit logged nothing (bug 2 regression)",
          "last commit" in ctx, f"got: {ctx[:80]!r}")

    ctx = run([], WORK + ["LOG.md"], doc_mtime_newer=True, tmp=tmp)
    check("silent when the last commit included LOG.md", ctx == "", f"got: {ctx[:80]!r}")

    ctx = run([], [], doc_mtime_newer=True, tmp=tmp)
    check("silent on a clean tree with no commit info", ctx == "", f"got: {ctx[:80]!r}")

    # --- thresholds and edge cases ---
    ctx = run(["src/a.py"], [], doc_mtime_newer=False, tmp=tmp)
    check("silent below the file threshold", ctx == "", f"got: {ctx[:80]!r}")

    ctx = run([], ["src/a.py"], doc_mtime_newer=True, tmp=tmp)
    check("silent for a small unlogged commit", ctx == "", f"got: {ctx[:80]!r}")

    mod.changed_files = lambda: None  # git unavailable
    mod.head_files = lambda: []
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.main()
    check("fails open when git cannot answer", buf.getvalue().strip() == "")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All docs-staleness tests passed")

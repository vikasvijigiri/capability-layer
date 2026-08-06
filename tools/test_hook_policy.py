#!/usr/bin/env python3
"""Enforce the hook policy: detect, deny, record state; never author strategy."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def require(label: str, condition: bool) -> None:
    if condition:
        print(f"OK: {label}")
    else:
        print(f"FAIL: {label}")
        failures.append(label)


def main_body_calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    return {
        node.func.id
        for node in ast.walk(main)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


bootstrap = ROOT / ".claude/hooks/session-start/02-bootstrap-docs.py"
drift = ROOT / ".claude/hooks/post-run/07-layer-drift.py"
require("bootstrap hook exists", bootstrap.is_file())
require("drift hook exists", drift.is_file())
if bootstrap.is_file():
    calls = main_body_calls(bootstrap)
    require("bootstrap main does not call strategic write helper", "write_if_missing" not in calls)
    require("bootstrap main does not create directories", "makedirs" not in calls and "mkdir" not in calls)
if drift.is_file():
    source = drift.read_text(encoding="utf-8")
    calls = main_body_calls(drift)
    require("drift hook declares read-only behavior", "never edits" in source)
    require("drift hook has no write calls", not calls.intersection({"open", "write_text", "write_bytes", "unlink", "remove", "rename", "mkdir", "makedirs"}))

if failures:
    raise SystemExit(1)
print("OK: hook policy preserves read-only detection and strategic-content safety")

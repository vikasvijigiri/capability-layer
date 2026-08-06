#!/usr/bin/env python3
"""Validate the bounded executable workflow contract without running agents."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".claude" / "workflows" / "feature-delivery.js"
text = WORKFLOW.read_text(encoding="utf-8")
failures: list[str] = []


def require(label: str, pattern: str) -> None:
    if re.search(pattern, text, re.MULTILINE):
        print(f"OK: {label}")
    else:
        print(f"FAIL: {label}")
        failures.append(label)


require("workflow exports meta", r"export\s+const\s+meta\s*=")
require("workflow has a name", r"name:\s*'feature-delivery'")
require("workflow accepts injected args", r"run\(\{\s*args:\s*workflowArgs")
require("workflow uses agent orchestration", r"await\s+agent\(")
require("workflow uses bounded pipeline", r"await\s+pipeline\(")
require("workflow has schemas", r"schema:\s*\{")
require("workflow filters null agents", r"filter\(completed\)")
require("workflow has plan approval boundary", r"planApproved\s*===\s*true")
require("workflow has release approval boundary", r"releaseApproved\s*===\s*true")
require("workflow has implementation stage", r"label:\s*'implement'")
require("workflow has independent reviews", r"const\s+reviewers\s*=")
require("workflow has release verification", r"label:\s*'release-readiness'")
require("workflow forbids deployment side effects", r"never\s+push,[\s\S]{0,40}merge,[\s\S]{0,40}deploy")
require("workflow documents bounded concurrency", r"at most two concurrent")

if text.count("agent(") < 5:
    failures.append("workflow has at least five lifecycle agents")
    print("FAIL: workflow has at least five lifecycle agents")
else:
    print("OK: workflow has at least five lifecycle agents")

if failures:
    raise SystemExit(1)

print("OK: feature-delivery workflow contract validated")

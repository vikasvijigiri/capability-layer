#!/usr/bin/env python3
"""Validate agent safety and portability invariants beyond basic routing."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude" / "agents"
READ_ONLY = {
    "Explore", "diff-reviewer", "failure-investigator", "spec-reviewer",
    "test-verifier", "architecture-reviewer", "security-reviewer",
    "release-verifier", "repo-cartographer",
}
failures: list[str] = []

for path in sorted(AGENTS.glob("*.md")):
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        failures.append(f"{path.name}: missing frontmatter")
        continue
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    name = fields.get("name", path.stem)
    tools = fields.get("tools", "")
    description = fields.get("description", "")
    if not fields.get("tools"):
        failures.append(f"{name}: missing explicit tools allowlist")
    if "mcp__" in tools:
        failures.append(f"{name}: harness-specific MCP tool in allowlist")
    if len(description) > 500:
        failures.append(f"{name}: description exceeds 500 characters")
    if "Do NOT use" not in description:
        failures.append(f"{name}: description lacks a Do NOT use boundary")
    if name in READ_ONLY and re.search(r"\b(Write|Edit)\b", tools):
        failures.append(f"{name}: read-only agent has a write tool")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}")
    raise SystemExit(1)

print(f"OK: {len(list(AGENTS.glob('*.md')))} agents satisfy safety and portability invariants")

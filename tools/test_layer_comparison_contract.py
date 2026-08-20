#!/usr/bin/env python3
"""Check that the all-surface comparison remains grounded in local inventory."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
HOOKS = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"
REGISTRY = ROOT / ".claude" / "hooks" / "hooks_registry.json"
REPORT = ROOT / "docs" / "research" / "2026-08-19-agent-layer-comparison.md"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    skills = sorted(SKILLS.glob("*/SKILL.md"))
    if len(skills) != 14:
        fail(f"comparison inventory expects 14 skills, found {len(skills)}")

    for path in skills:
        text = path.read_text(encoding="utf-8")
        if "## Success" not in text or "## Routing" not in text:
            fail(f"skill lacks Success and Routing contracts: {path.relative_to(ROOT)}")
        if not re.search(r"(?i)\b(output|report|artifact|handoff|verification|evidence)\b", text):
            fail(f"skill lacks an output or evidence contract: {path.relative_to(ROOT)}")

    try:
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"settings.json is unreadable: {exc}")

    registered: set[Path] = set()
    for groups in settings.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                match = re.search(r"\.claude/hooks/([^\"']+\.py)", hook.get("command", ""))
                if match:
                    registered.add(HOOKS / match.group(1))

    executable = {
        path
        for path in HOOKS.glob("*/*.py")
        if not path.name.startswith("_") and path.name != "check_config_json.py"
    }
    if len(executable) != 18:
        fail(f"comparison inventory expects 18 executable hooks, found {len(executable)}")
    if registered != executable:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        documented = {
            ROOT / path
            for path in registry.get("events", {}).get("post-run-steps", {}).get("subscribers", [])
        }
        if executable - registered != documented:
            missing = sorted(str(path.relative_to(ROOT)) for path in executable - registered - documented)
            fail(f"unregistered executable hooks lack manual-only documentation: {missing}")
        if registered - executable:
            extra = sorted(str(path.relative_to(ROOT)) for path in registered - executable)
            fail(f"settings registers missing executable hooks: {extra}")

    for path in sorted(executable):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not ast.get_docstring(tree):
            fail(f"hook lacks a module contract docstring: {path.relative_to(ROOT)}")
        source = path.read_text(encoding="utf-8")
        if "load_payload" not in source:
            fail(f"hook does not load its event payload: {path.relative_to(ROOT)}")

    report = REPORT.read_text(encoding="utf-8")
    for marker in ("## Findings", "## Disagreements", "## Not adopted", "## Sources", "14 skills", "18 executable event hooks"):
        if marker not in report:
            fail(f"comparison report missing {marker!r}")
    for source in ("obra/superpowers", "anthropics/skills", "github/awesome-copilot"):
        if source not in report:
            fail(f"comparison report missing primary source {source!r}")

    print("OK: 14 skills and 18 executable hooks have local contracts")
    print("OK: comparison report names the inventory, evidence boundaries, and three primary repositories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

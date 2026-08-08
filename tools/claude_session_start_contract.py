from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_JSON = ROOT / ".claude" / "settings.json"
BOOTSTRAP_SCRIPT = ROOT / ".claude" / "hooks" / "session-start" / "02-bootstrap-docs.py"
STATE_SCRIPT = ROOT / ".claude" / "hooks" / "session-start" / "03-state-report.py"
WORKFLOW_MD = ROOT / ".claude" / "workflow.md"

EXPECTED_BOOTSTRAP_FILES = [
    "README.md",
    "CLAUDE.md",
    "TASK.md",
    "MEMORY.md",
    "HANDOFF.md",
    "LOG.md",
    "ISSUES.md",
]

EXPECTED_SESSION_START_SCRIPT_RELATIVES = [
    ".claude/hooks/session-start/02-bootstrap-docs.py",
    ".claude/hooks/session-start/03-state-report.py",
]


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {SETTINGS_JSON}: {exc}") from exc


def session_start_commands(settings: dict) -> list[str]:
    commands: list[str] = []
    hooks = settings.get("hooks", {})
    for entry in hooks.get("SessionStart", []):
        for hook in entry.get("hooks", []):
            cmd = hook.get("command")
            if isinstance(cmd, str):
                commands.append(cmd)
    return commands


def list_bootstrap_files() -> list[str]:
    text = BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")
    module = ast.parse(text)
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "BOOTSTRAP_FILES":
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    return [ast.literal_eval(elt) for elt in node.value.elts]
    raise ValueError("BOOTSTRAP_FILES not found in 02-bootstrap-docs.py")


def state_report_source() -> str:
    return STATE_SCRIPT.read_text(encoding="utf-8")


def workflow_state_tags() -> set[str]:
    text = WORKFLOW_MD.read_text(encoding="utf-8")
    return {match.group(1) for match in re.finditer(r"\[state:([^\]]+)\]", text)}

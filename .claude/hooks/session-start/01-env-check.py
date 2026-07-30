"""session-start -- validates .claude/ structure and registries against convention.

Drift detection, not a gate: it reports and never blocks, because a session that
cannot start is far worse than one that starts with a stale registry.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CLAUDE_DIR = ROOT / ".claude"
# `capabilities` was removed on 2026-07-31; its nine index files collapsed into
# `routing/capabilities.md` and its superseded artefact copies were deleted.
KNOWN_DIRS = {"agents", "blueprints", "commands", "hooks", "mcps", "playbooks",
              "registry", "routing", "skills", "templates", "validators",
              "workflows"}
KNOWN_FILES = {"README.md", "settings.json", "settings.local.json",
               "PREREQUISITES.md"}


def collect_issues():
    issues = []

    for reg in ("agents.json", "capabilities.json", "mcps.json"):
        path = CLAUDE_DIR / "registry" / reg
        if not path.exists():
            issues.append(f"missing registry: {reg}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not any(data.values()):
                issues.append(f"empty registry: {reg}")
        except Exception as exc:
            issues.append(f"unreadable registry {reg}: {exc}")

    if CLAUDE_DIR.exists():
        for entry in CLAUDE_DIR.iterdir():
            if entry.is_dir() and entry.name not in KNOWN_DIRS:
                issues.append(f"unexpected directory under .claude/: {entry.name}")
            if entry.is_file() and entry.name not in KNOWN_FILES:
                issues.append(f"unexpected file under .claude/: {entry.name}")

    return issues


def main():
    load_payload()  # drain stdin so the harness is never left waiting on us
    write_log("session-start.log", "SESSION-START", {"issues": collect_issues()})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

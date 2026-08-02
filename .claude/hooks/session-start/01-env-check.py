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
# `.claude/` holds exactly this and nothing else. Anything new here is reported
# rather than silently tolerated -- an unrecognised file is usually a leftover
# from something deleted, and this repo has been bitten by those repeatedly.
#
# README.md and PREREQUISITES.md were removed on 2026-08-01: both duplicated
# CLAUDE.md or described capabilities that no longer exist, and neither was
# referenced by anything. Their two load-bearing facts moved to CLAUDE.md's
# Gotchas. Re-add a name here only when a file genuinely belongs in `.claude/`.
KNOWN_DIRS = {"agents", "commands", "hooks", "routing", "skills"}
# `workflow.md` moved here from `docs/` on 2026-08-02: it is the stage -> skill
# chain the routing file and every skill's handoff refer to, so it belongs
# beside them rather than in the docs tree.
KNOWN_FILES = {"settings.json", "settings.local.json", "workflow.md"}


def collect_issues():
    issues = []

    # Every skill must have a SKILL.md and a routing entry -- with the capability
    # router gone, `routing/process-skills.md` is the only signal that survives
    # skill-listing truncation, so an unrouted skill is an invisible one.
    skills_dir = CLAUDE_DIR / "skills"
    routing = CLAUDE_DIR / "routing" / "process-skills.md"
    routed = routing.read_text(encoding="utf-8") if routing.exists() else ""
    if not routing.exists():
        issues.append("missing .claude/routing/process-skills.md")
    if skills_dir.exists():
        for skill in sorted(p.name for p in skills_dir.iterdir() if p.is_dir()):
            if not (skills_dir / skill / "SKILL.md").exists():
                issues.append(f"skill without SKILL.md: {skill}")
            if f"## {skill}" not in routed:
                issues.append(f"skill with no routing entry: {skill}")

    if CLAUDE_DIR.exists():
        for entry in CLAUDE_DIR.iterdir():
            if entry.is_dir() and entry.name not in KNOWN_DIRS:
                issues.append(f"unexpected directory under .claude/: {entry.name}")
            if entry.is_file() and entry.name not in KNOWN_FILES:
                issues.append(f"unexpected file under .claude/: {entry.name}")

    return issues


def main():
    load_payload()  # drain stdin so the harness is never left waiting on us
    issues = collect_issues()
    write_log("session-start.log", "SESSION-START", {"issues": issues})

    # Surface them. Until 2026-08-02 this hook only ever wrote to the log, so
    # every finding it made was invisible in the session it was made in -- an
    # unrouted skill and a stray `.claude/` file had been sitting in
    # session-start.log unread. A check nobody sees is not a check.
    #
    # Silent when clean: a clean start must stay quiet, or the noise trains the
    # reader to skip the one start that was not clean.
    if issues:
        lines = ["`.claude/` structure check found "
                 f"{len(issues)} issue{'s' if len(issues) > 1 else ''}:"]
        lines += [f"- {i}" for i in issues]
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(lines),
            }
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

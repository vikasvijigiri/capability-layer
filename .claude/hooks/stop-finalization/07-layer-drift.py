"""post-run -- read-only capability-layer drift detector.

This hook detects stale references and harness-contract drift after a turn. It
never edits strategic documents, capability files, source, or configuration;
it only reports evidence and leaves repair to the owning skill.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CHECKS = (
    ("referenced paths", [sys.executable, "tools/test_referenced_paths.py"]),
    ("harness contract", [sys.executable, "tools/test_harness_contract.py"]),
)


def run_check(label: str, command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"{label}: could not run ({exc})"
    if result.returncode == 0:
        return None
    detail = (result.stdout + "\n" + result.stderr).strip().splitlines()
    return f"{label}: failed; {detail[-1] if detail else 'no diagnostic'}"


def main() -> int:
    if os.environ.get("UAIOS_NO_LAYER_DRIFT"):
        return 0
    load_payload()
    findings = [finding for label, command in CHECKS if (finding := run_check(label, command))]
    if not findings:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": (
                "Capability-layer drift detected (read-only): "
                + " | ".join(findings)
                + ". Repair through the documented owner; this hook did not edit files."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Detection must never wedge a session.
        raise SystemExit(0) from None

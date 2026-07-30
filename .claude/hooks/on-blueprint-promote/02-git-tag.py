"""on-blueprint-promote -- a blueprint was promoted to canonical.

Not registered in settings.json and deliberately so: promoting a blueprint is a
domain action, not a moment in a session, so no lifecycle event corresponds to
it. Whatever performs the promotion invokes it:

    python tools/run_hook.py on-blueprint-promote '{"blueprint": {"name": "x"}}'

Tagging stays behind ENABLE_GIT_TAG=1 -- writing a git tag is a side effect on a
shared repo and must be opted into, not inherited from a log-only hook firing.
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402


def main():
    payload = load_payload()
    write_log("blueprint-tag.log", "GIT-TAG", payload)

    blueprint = payload.get("blueprint") or {}
    name = blueprint.get("name") if isinstance(blueprint, dict) else None
    if os.environ.get("ENABLE_GIT_TAG") != "1" or not name:
        return

    try:
        subprocess.run(
            ["git", "tag", "-a", f"blueprint/{name}", "-m", "Promoted blueprint"],
            check=True, capture_output=True, timeout=30,
        )
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

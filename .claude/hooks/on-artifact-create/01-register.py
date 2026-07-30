"""on-artifact-create -- a new artifact landed on disk.

Registered on PostToolUse with a `Write` matcher, so the harness has already
narrowed this to file creation before the script runs. Validators also invoke it
directly on a passing run, per CLAUDE.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402


def main():
    write_log("artifact-create.log", "ARTIFACT-CREATE", load_payload())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

"""post-run -- fires on Stop, i.e. when a turn finishes.

Appends the audit trail entry. Pairs with pre-run/01-log.py: one line in each
log per turn, so a run that started but never finished is visible as a gap.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402


def main():
    write_log("post-run.log", "POST-RUN", load_payload())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

"""on-error -- fires on PostToolUseFailure, i.e. after any tool call fails.

Deliberately unfiltered: every failure is recorded, whatever the tool. The
narrower views (a failed validator, a failed deploy) are separate hooks on the
same event that filter for themselves.

Note on the payload: the failure reason is in `error`, not `error_message` as
the published reference states -- measured from a live payload. `is_interrupt`
distinguishes a user Ctrl-C from a genuine failure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402


def main():
    payload = load_payload()
    if payload.get("is_interrupt"):
        return  # user cancelled; not an error worth recording
    write_log("error.log", "ERROR", payload)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

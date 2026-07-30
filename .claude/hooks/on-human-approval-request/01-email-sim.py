"""on-human-approval-request -- a human is being asked to approve something.

Registered on Notification with a `permission_prompt` matcher. Notification also
covers idle prompts and auth events, which are not approval requests, so the
matcher is what keeps this log meaningful.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402


def main():
    write_log("approval-requests.log", "APPROVAL-REQ", load_payload())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

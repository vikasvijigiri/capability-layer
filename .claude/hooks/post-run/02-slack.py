"""post-run -- fires on Stop. Best-effort Slack notification.

Posts only when SLACK_WEBHOOK is set; otherwise it just logs, so an unconfigured
machine is silent rather than erroring. A failed post is swallowed on purpose --
a notification that cannot be delivered must not fail the turn it describes.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402


def main():
    payload = load_payload()
    write_log("post-run-slack.log", "POST-RUN-SLACK", payload)

    webhook = os.environ.get("SLACK_WEBHOOK")
    if not webhook:
        return
    try:
        import requests
        requests.post(webhook, json={"text": f"Post-run: {payload}"}, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

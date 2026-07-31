"""on-human-approval-request -- a human is being asked to approve something.

Registered on `PermissionRequest`, verified against the live harness on
2026-07-31. The payload carries `tool_name`, `tool_input`,
`permission_suggestions`, `permission_mode`, `session_id`, `prompt_id`, `cwd`
and `transcript_path`.

It was registered on `Notification` with a `permission_prompt` matcher until
then, and had never fired once: all 37 log entries were synthetic payloads from
`tools/run_hook.py`, none carrying `session_id`. Removing the matcher entirely
changed nothing across two real permission prompts, which ruled out the matcher
and proved this build does not emit `Notification` for permission prompts at
all. Feeding the script a payload directly did write a line, which ruled out the
writer. Wrong event, not wrong filter.

The lesson worth keeping: `tools/test_hooks.py` passed this hook on every run,
because it invokes the script directly and therefore tests the script, never the
registration. A hook suite cannot tell you a hook is wired to an event that does
not exist. Only a real payload can, and `session_id` is the tell -- synthetic
payloads never have one.
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

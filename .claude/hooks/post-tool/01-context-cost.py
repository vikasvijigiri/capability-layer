"""post-tool -- reports what a tool call just bought in permanent context.

The measurement that motivated this
-----------------------------------
A session's cost is `API calls x accumulated context`, and every tool INPUT
stays in context for the rest of the session. Measured over one session's
transcript, the largest single contributor was not file reads:

    645,855 chars  ~161,463 tok  Bash (input)
    558,270 chars  ~139,567 tok  Bash (result)
    384,216 chars  ~ 96,054 tok  Edit (input)

Bash *inputs* beat Bash *results*. That is inline scripts -- heredocs written
into the command itself, mostly throwaway measurement code. Each one is paid
once when written and then again on every later request in the session.

Reports, never gates -- which is why it is PostToolUse
------------------------------------------------------
It was written against `pre-run` first and `test_hook_standards.py` refused it:
a `PreToolUse` hook must carry `deny(` or `permissionDecision`, because one that
returns silently is indistinguishable from one that crashed. The standard is
right and the hook was in the wrong event. Satisfying it by emitting
`permissionDecision: "allow"` would have auto-approved every shell command in
the session -- a real safety regression bought to quiet a check.

A big command is sometimes correct: a here-doc that writes a real file, a loop
driving a multi-file edit. So this reports and gets out of the way. The cost of
the call it measures is already paid; the saving is on the next one, and a
session makes hundreds.

`decisions/2026-08-02-gate-on-blast-radius.md` puts a reversible, local action
in the "act" band -- a long command is not dangerous, only expensive, so a
warning is the proportionate mechanism.

Names no skill, per `decisions/2026-08-04-hooks-never-name-a-skill.md`.

Fire it directly:

    python tools/run_hook.py post-tool '{"tool_name":"Bash","tool_input":{"command":"..."}}'
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from _hooklib import load_payload
except Exception:  # pragma: no cover - a guard that cannot load must not wedge
    sys.exit(0)

# Chosen from the measured distribution rather than by feel. Ordinary commands
# in this repository -- a git query, a grep, a single script invocation -- sit
# under 300 chars. The inline analysis scripts that dominated the transcript ran
# 800-2,000. 700 sits in the gap, so routine work never sees this and a script
# pasted into the command line always does.
WARN_CHARS = 700

# Tools whose input is authored prose rather than a command. A long `Write` is
# the file itself and there is nothing cheaper to suggest, so it is excluded --
# warning about it would be noise, and noise is what gets a hook switched off.
WATCHED = ("Bash", "PowerShell")


def main() -> int:
    payload = load_payload() or {}
    name = payload.get("tool_name") or ""
    if name not in WATCHED:
        return 0

    body = payload.get("tool_input") or {}
    command = str(body.get("command") or "")
    if len(command) < WARN_CHARS:
        return 0

    tokens = len(command) // 4
    print(
        f"[context cost] that {name} command was {len(command):,} chars "
        f"(~{tokens:,} tokens) and now stays in context for the rest of the "
        f"session, re-read on every later request.\n"
        f"  Cheaper, in order: a dedicated tool (Grep/Read/Glob) instead of a "
        f"shell equivalent; a narrower query; or -- if the script is worth "
        f"keeping -- write it to a file once and run the path.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

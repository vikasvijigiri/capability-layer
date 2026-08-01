"""Shared helpers for this repo's hook scripts.

Every hook here has two callers and must behave identically for both:

  Claude Code       registers the script directly in .claude/settings.json and
                    delivers the payload as JSON on stdin.
  a validator       runs `python tools/run_hook.py <event> '<json>'`, which
                    delivers the payload in the HOOK_PAYLOAD env var. CLAUDE.md
                    requires validators to do this, so it cannot be dropped.

`load_payload()` accepts either, so a hook never cares which one invoked it.

Not placed inside an event directory on purpose: run_hook.py executes every
file in `.claude/hooks/<event>/`, so a helper module living there would be
run as though it were a hook.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent


def load_payload() -> dict:
    """Return the hook payload from HOOK_PAYLOAD or stdin, whichever is present.

    HOOK_PAYLOAD is checked FIRST, and the ordering is load-bearing, not a
    preference. run_hook.py launches hooks without redirecting stdin, so the
    child inherits the parent's stdin -- which, when the parent was itself
    launched from a pipe, is an open handle that never reaches EOF. Reading it
    blocks forever and hangs the whole run. `isatty()` does not save you: an
    inherited pipe is not a TTY, so the guard passes and the read still blocks.

    Checking the env var first means the only caller that leaves stdin dangling
    never reaches the stdin branch at all. Claude Code sets no HOOK_PAYLOAD and
    always writes real JSON to stdin, so it falls through correctly.
    """
    raw = os.environ.get("HOOK_PAYLOAD", "")

    if not raw.strip():
        try:
            if not sys.stdin.isatty():
                raw = sys.stdin.read()
        except Exception:
            raw = ""

    if not raw.strip():
        return {}

    try:
        data = json.loads(raw)
    except Exception:
        return {"raw": raw}
    return data if isinstance(data, dict) else {"raw": data}


def write_log(filename: str, prefix: str, payload) -> None:
    """Append one line to a log beside this module.

    The path is absolute. The original versions of these hooks wrote to
    './.claude/hooks/*.log', which silently scattered logs into whatever
    directory the caller happened to be in.
    """
    try:
        with (HOOKS_DIR / filename).open("a", encoding="utf-8") as handle:
            handle.write(f"{prefix}: {json.dumps(payload)}\n")
    except Exception:
        pass


def command_of(payload: dict) -> str:
    """The shell command for a tool-related payload, or '' for anything else."""
    tool_input = payload.get("tool_input") or {}
    return tool_input.get("command") or "" if isinstance(tool_input, dict) else ""


def deny(reason: str, event: str = "PreToolUse") -> None:
    """Block the pending action. Only meaningful on PreToolUse."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


# --- turn-scoped knowledge-doc snapshot -------------------------------------
#
# `pre-run/04-docs-staleness.py` records the docs' content at UserPromptSubmit;
# `post-run/05-docs-gate.py` compares at Stop. A digest change means this turn
# wrote them.
#
# This exists because the gate previously compared mtimes, which false-blocked
# three times on 2026-08-01 with the docs correctly written -- git's index
# refresh bumps working-file mtimes, and an uncommitted backlog keeps old ones
# forever. Content answers "was it written this turn"; timestamps only ever
# approximated it. See decisions/2026-08-01-docs-gate-compares-content.md.

TURN_MARKER = HOOKS_DIR / "state" / "docs-turn-marker.json"
TRACKED_DOCS = ("LOG.md", "HANDOFF.md")


def doc_digests(repo_root=None) -> dict:
    """sha256 per tracked knowledge doc. A missing file digests as '' , not an error."""
    import hashlib
    root = Path(repo_root) if repo_root else HOOKS_DIR.parents[1]
    out = {}
    for name in TRACKED_DOCS:
        try:
            out[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        except OSError:
            out[name] = ""
    return out


def save_turn_marker(repo_root=None) -> None:
    """Snapshot the docs at the start of a turn. Never raises."""
    try:
        TURN_MARKER.parent.mkdir(parents=True, exist_ok=True)
        TURN_MARKER.write_text(json.dumps(doc_digests(repo_root)), encoding="utf-8")
    except Exception:
        pass


def load_turn_marker():
    """The snapshot, or None when there isn't a usable one (first turn, or corrupt)."""
    try:
        data = json.loads(TURN_MARKER.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None

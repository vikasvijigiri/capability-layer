"""post-tool -- names a call this session has already made, with the same inputs.

The gap this closes
-------------------
`Agentic Workflows (IDE)` §10 makes an anti-repetition layer a first-class
component: before any meaningful operation, ask whether we have already read
this file, already queried this API, already established this fact. §25 puts it
as "Repetition is a defect" and "Reuse before retrieve".

Nothing in this layer implemented it. `tools/memory.py` reads MEMORY.md, the
chain ledger records states, `bench.py` records costs -- none of them answer
"did I already run exactly this?".

Why a report rather than a cache
--------------------------------
A hook cannot serve a cached result: PostToolUse fires *after* the call, so the
tokens and the latency are already spent. What it can do is make the SECOND
occurrence visible, which is what changes the third. The same reasoning as
`01-context-cost.py` beside it -- the cost of the call it measures is already
paid, and the saving is on the next one.

Blocking was considered and rejected. A repeated call is often legitimate: a
test re-run after an edit, a `git status` before and after a commit, a file read
again because it changed. Denying those would be wrong, and a gate that is wrong
often gets switched off, taking the true positives with it.

What counts as the same call
----------------------------
The tool name plus its salient input, normalised. For Bash that is the command
with runs of whitespace collapsed, so re-indentation does not read as a new
call. Volatile commands are exempt by prefix -- re-running `git status` is how
you observe a change, not a repetition.

Fire it directly:

    python tools/run_hook.py post-tool '{"tool_name":"Bash","tool_input":{"command":"ls"}}'
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from _hooklib import load_payload
except Exception:  # pragma: no cover - a reporter that cannot load must not wedge
    sys.exit(0)

STATE = Path(__file__).resolve().parents[1] / "state" / "call-fingerprints.json"

# Observing state is not repeating work. These re-read something that changes,
# which is the whole point of running them twice.
VOLATILE = ("git status", "git diff", "git log", "git branch", "ls", "pwd",
            "date", "cat .claude/hooks/state", "python tools/resume.py",
            "python tools/run_checks", "python tools/bench.py", "gh run",
            "python tools/chain.py")

# Shell calls only, and that is a cost decision rather than an oversight. Read
# and Grep are the most frequent tools in a session, so watching them means a
# Python process spawn (~60ms) on each one -- paid on every call to catch the
# few that repeat. Shell calls are the expensive, most-repeated kind and the
# ones worth a spawn. `settings.json` matches `Bash|PowerShell` to suit; if that
# matcher is ever widened, widen this in step or the hook runs and says nothing.
WATCHED = ("Bash", "PowerShell")

# Below this, the call is too cheap for the notice to be worth its own tokens.
MIN_CHARS = 40

# A session's fingerprints. Older entries are dropped so the file cannot grow
# without bound in a long session; 400 covers far more calls than a session
# makes and keeps the file under ~40KB.
MAX_ENTRIES = 400


def salient(name: str, body: dict) -> str:
    """The part of the input that decides whether two calls are the same."""
    if name in ("Bash", "PowerShell"):
        return str(body.get("command") or "")
    if name == "Read":
        return str(body.get("file_path") or "")
    if name == "Grep":
        return f"{body.get('pattern') or ''}|{body.get('path') or ''}|{body.get('glob') or ''}"
    if name == "WebFetch":
        return str(body.get("url") or "")
    return ""


def load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(seen: dict) -> None:
    if len(seen) > MAX_ENTRIES:
        oldest = sorted(seen.items(), key=lambda kv: kv[1]["at"])
        seen = dict(oldest[-MAX_ENTRIES:])
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(seen), encoding="utf-8")
    except OSError:
        pass  # a reporter that cannot persist still must not break the turn


def main() -> int:
    payload = load_payload() or {}
    name = payload.get("tool_name") or ""
    if name not in WATCHED:
        return 0

    text = salient(name, payload.get("tool_input") or {})
    if len(text) < MIN_CHARS:
        return 0

    normalised = re.sub(r"\s+", " ", text).strip()
    if any(normalised.startswith(v) for v in VOLATILE):
        return 0

    key = hashlib.sha256(f"{name}\x00{normalised}".encode()).hexdigest()[:16]
    seen = load()
    now = time.time()
    prior = seen.get(key)

    seen[key] = {"at": now, "n": (prior or {}).get("n", 0) + 1,
                 "preview": normalised[:70]}
    save(seen)

    if not prior:
        return 0

    ago = int(now - prior["at"])
    when = f"{ago}s ago" if ago < 120 else f"{ago // 60}m ago"
    print(
        f"[repeat] this exact {name} already ran {when} "
        f"(occurrence {seen[key]['n']}): {normalised[:70]}\n"
        f"  Its result is already in this session's context -- reuse it rather "
        f"than re-reading. If the answer genuinely changed, say what changed it.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

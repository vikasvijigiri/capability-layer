"""context-budget -- reports what a tool call just bought in permanent context.

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

import hashlib
import json
import re
import sys
import time
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


# --- second check: this call already happened ---------------------------------
#
# `Agentic Workflows (IDE)` section 10 makes an anti-repetition layer
# first-class -- "Repetition is a defect", "Reuse before retrieve" -- and nothing
# implemented it. It lives HERE rather than in a hook of its own, and that is a
# measured decision: two PostToolUse scripts cost two Python process spawns on
# every shell call, 215ms + 226ms = 441ms, paid whether or not either fires. One
# process runs both checks for ~220ms. In a 90-call session that is 40 seconds
# against 20.
#
# It cannot serve a cached result -- PostToolUse fires after the call, so the
# tokens and the latency are already spent. Making the SECOND occurrence visible
# is what changes the third. Blocking was rejected: a repeat is often
# legitimate (a suite re-run after an edit, a file re-read because it changed),
# and denying those trains people to switch the hook off.
STATE = Path(__file__).resolve().parents[1] / "state" / "call-fingerprints.json"

# Observing state is not repeating work: these re-read something that changes,
# which is the entire reason to run them twice.
VOLATILE = ("git status", "git diff", "git log", "git branch", "ls", "pwd",
            "date", "cat .claude/hooks/state", "python tools/resume.py",
            "python tools/run_checks", "python tools/bench.py", "gh run",
            "python tools/chain.py")

# Every real command in this environment is wrapped `cd "<dir>" && <command>`
# (or `; `), so a bare `startswith()` against VOLATILE never matches -- a
# repo-wide check of this session's own transcript found `git status`,
# `tools/resume.py` and similar intentionally-exempt commands were NOT being
# excluded, inflating the reported duplicate-call rate with false positives.
# Stripped only for the VOLATILE/MIN_REPEAT_CHARS checks below, never for the
# fingerprint hash -- genuine repeat detection must keep hashing the full
# command, wrapper included, since that is what actually repeats verbatim.
_CD_PREFIX_RE = re.compile(r'^cd\s+(?:"[^"]*"|\'[^\']*\'|\S+)\s*(?:&&|;)\s*')


def _strip_cd_prefix(command: str) -> str:
    return _CD_PREFIX_RE.sub("", command, count=1)


# Below this the call is too cheap for the notice to be worth its own tokens.
# Measured against the command with any `cd ... &&` wrapper stripped -- the
# wrapper's own length must not count toward "is this substantial enough to
# flag", or a trivial `ls` clears the floor on the wrapper alone.
MIN_REPEAT_CHARS = 40

# Bounded so a long session cannot grow the file without limit.
MAX_ENTRIES = 400


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(seen: dict) -> None:
    if len(seen) > MAX_ENTRIES:
        totals = seen.get(TOTALS)
        calls = {k: v for k, v in seen.items() if k != TOTALS}
        # Trim the fingerprints, never the totals -- dropping those would make a
        # long session look cheaper than a short one, which is the opposite of
        # what the counter is for.
        seen = dict(sorted(calls.items(), key=lambda kv: kv[1]["at"])[-MAX_ENTRIES:])
        if totals is not None:
            seen[TOTALS] = totals
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(seen), encoding="utf-8")
    except OSError:
        pass  # a reporter that cannot persist still must not break the turn


# Reserved key inside the same state file. Sixteen hex characters is the shape
# of every other key, so a name starting with an underscore cannot collide.
#
# `Agentic Workflows (IDE)` section 21 requires `tools_called` and
# `api_call_count` per run and derives "tool calls / successful task" from them.
# Nothing in this layer counted either, which is why objective 4 could be
# asserted but never graded -- and an objective that cannot be measured is one
# nobody can tell they are failing. Counting happens for EVERY watched call,
# including the volatile and short ones the repeat check skips, because the
# question "how many calls did this session make" does not care why.
TOTALS = "_totals"


def bump_totals(seen: dict, chars: int, repeated: bool) -> None:
    t = seen.get(TOTALS) or {"calls": 0, "chars": 0, "repeats": 0}
    t["calls"] += 1
    t["chars"] += chars
    t["repeats"] += 1 if repeated else 0
    seen[TOTALS] = t


def repeat_notice(name: str, command: str) -> str:
    """The notice for a command this session already ran, or '' for a new one."""
    seen = _load()
    normalised = re.sub(r"\s+", " ", command).strip()
    check_target = _strip_cd_prefix(normalised)
    skip = (len(check_target) < MIN_REPEAT_CHARS
            or any(check_target.startswith(v) for v in VOLATILE))
    if skip:
        # Still counted. The totals answer "how many calls did this session
        # make", which does not care whether the call was worth fingerprinting.
        bump_totals(seen, len(command), False)
        _save(seen)
        return ""

    key = hashlib.sha256(f"{name}\x00{normalised}".encode()).hexdigest()[:16]
    now = time.time()
    prior = seen.get(key)
    seen[key] = {"at": now, "n": (prior or {}).get("n", 0) + 1}
    bump_totals(seen, len(command), bool(prior))
    _save(seen)
    if not prior:
        return ""

    ago = int(now - prior["at"])
    when = f"{ago}s ago" if ago < 120 else f"{ago // 60}m ago"
    return (
        f"[repeat] this exact {name} already ran {when} "
        f"(occurrence {seen[key]['n']}): {normalised[:70]}\n"
        f"  Its result is already in this session's context -- reuse it rather "
        f"than running it again. If the answer genuinely changed, say what "
        f"changed it."
    )


def main() -> int:
    payload = load_payload() or {}
    name = payload.get("tool_name") or ""
    if name not in WATCHED:
        return 0

    body = payload.get("tool_input") or {}
    command = str(body.get("command") or "")

    notices = []
    if len(command) >= WARN_CHARS:
        tokens = len(command) // 4
        notices.append(
            f"[context cost] that {name} command was {len(command):,} chars "
            f"(~{tokens:,} tokens) and now stays in context for the rest of the "
            f"session, re-read on every later request.\n"
            f"  Cheaper, in order: a dedicated tool (Grep/Read/Glob) instead of a "
            f"shell equivalent; a narrower query; or -- if the script is worth "
            f"keeping -- write it to a file once and run the path."
        )

    repeat = repeat_notice(name, command)
    if repeat:
        notices.append(repeat)

    if notices:
        print("\n".join(notices), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

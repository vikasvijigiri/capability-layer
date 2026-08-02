"""
PostToolUse hook -- measures how many bytes each tool result pours into the
context window, and says so when the number stops being incidental.

Why this exists
---------------
On 2026-08-02 a research session ingested roughly 135,000 characters of source
material (four GitHub SKILL.md files read whole, a 71k-char file sliced three
times, six local files read whole) to produce two reports totalling 24,000.
Every one of those bytes stays resident and is re-sent on every later turn.

The failure is not that any single read was wrong -- each was defensible. It is
that ingestion has no running total, so the cost is invisible until the session
is already expensive. Nothing in the transcript ever says "you have read 135k
characters." The model cannot economise against a number it cannot see.

The same session had already written down the fix, in
`docs/research/2026-08-02-generic-pipeline-skillset.md`: *extract, don't
ingest*. A written rule that the writer violated in the same turn is exactly the
kind of rule this repo replaces with a mechanism.

What it does
------------
Accumulates result sizes per session in `state/context-budget.json` and emits
`additionalContext` on two triggers only:

- **A single fat result** (>= SINGLE_WARN chars). Names the cheaper route for
  that specific tool, because the cheaper route differs by tool: a directory
  listing instead of a file read, `offset`/`limit` instead of a whole file,
  a `Grep` instead of a `Read`.
- **Each cumulative step crossed** (every BUDGET_STEP chars). Reports the total
  and the three biggest single reads, so the advice names real offenders rather
  than scolding in general.

Silent otherwise, and each cumulative step speaks at most once per session --
a warning that repeats is a warning that gets filtered out.

Never blocks. PostToolUse cannot un-read the bytes; this is a meter, not a gate.
Fails open: any error means no output at all, which is the same as a quiet turn.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

STATE = Path(__file__).resolve().parents[1] / "state" / "context-budget.json"

# Thresholds in characters, roughly 4 chars per token.
#
# SINGLE_WARN is calibrated against the four fattest reads of the 2026-08-02
# session that motivated this hook: 20,000 / 17,000 / 11,000 / 9,300 chars.
# A 20,000 threshold caught one of the four and would have stayed silent through
# the run that prompted the user to ask why the session was so expensive.
# 12,000 catches the top two -- the ones with a genuinely cheaper alternative --
# and leaves ordinary source files alone.
SINGLE_WARN = 12_000    # ~3k tokens in one result
BUDGET_STEP = 150_000   # ~37k tokens cumulative, then again at each multiple
TOP_N = 3
MAX_SESSIONS = 20       # keep the state file bounded

# Tool name -> the cheaper thing to do instead. Only consulted for the
# single-result warning, where the advice can be specific enough to act on.
CHEAPER = {
    "Read": "read a slice (`offset`/`limit`), or `Grep` for the lines you need",
    "Bash": "pipe through `head`, or write the output to a file and slice it",
    "PowerShell": "`Select-Object -First N`, or write to a file and slice it",
    "WebFetch": "ask a narrower `prompt` so less of the page comes back",
    "mcp__github__get_file_contents":
        "list the directory with `fields: [name, size]` first -- sizes answer "
        "structural questions without reading anything",
    "mcp__fetch__fetch": "use `max_length`, or fetch the specific section",
}
DEFAULT_CHEAPER = "fetch metadata first, then read only the part you need"


def result_size(payload):
    """Characters in the tool result, across the shapes it actually arrives in.

    Deliberately forgiving: an unrecognised shape measures 0 and the hook stays
    quiet. Over-reporting on a shape we guessed wrong would be worse than
    missing one -- a meter nobody trusts gets ignored.
    """
    resp = payload.get("tool_response")
    if resp is None:
        resp = payload.get("tool_result")
    if resp is None:
        return 0
    if isinstance(resp, str):
        return len(resp)
    if isinstance(resp, dict):
        total = 0
        for key in ("content", "text", "stdout", "output", "result"):
            val = resp.get(key)
            if isinstance(val, str):
                total += len(val)
            elif isinstance(val, list):
                total += sum(len(b.get("text", "")) if isinstance(b, dict)
                             else len(str(b)) for b in val)
        return total
    if isinstance(resp, list):
        return sum(len(b.get("text", "")) if isinstance(b, dict) else len(str(b))
                   for b in resp)
    return 0


def target_of(payload):
    """A short label for what was read, for the offender list.

    Paths keep their parent directory. A bare basename is useless here: the
    fattest reads of the motivating session were four different repos' files
    all named `SKILL.md`, and an offender list naming `SKILL.md` three times
    tells you nothing about which read to have done differently.
    """
    ti = payload.get("tool_input") or {}
    for key in ("file_path", "url", "path", "command", "pattern", "query"):
        val = ti.get(key)
        if not isinstance(val, str) or not val.strip():
            continue
        val = val.strip()
        if key in ("file_path", "path"):
            parts = val.replace("\\", "/").rstrip("/").split("/")
            return "/".join(parts[-2:]) if len(parts) > 1 else parts[-1]
        return val[:60]
    return "?"


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    except Exception:
        pass


def emit(text):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


def main():
    payload = load_payload()
    if not isinstance(payload, dict):
        return

    size = result_size(payload)
    if size <= 0:
        return

    tool = payload.get("tool_name") or "?"
    session = str(payload.get("session_id") or "default")

    state = load_state()
    entry = state.get(session) or {"total": 0, "biggest": [], "steps_warned": []}
    entry["total"] = int(entry.get("total", 0)) + size

    biggest = entry.get("biggest") or []
    biggest.append({"tool": tool, "target": target_of(payload), "chars": size})
    biggest.sort(key=lambda r: -r.get("chars", 0))
    entry["biggest"] = biggest[:TOP_N]

    messages = []

    if size >= SINGLE_WARN:
        # Name the target, not just the tool. "That Read was 20,000 chars" is
        # unactionable when the turn made four reads; the label is how you know
        # which one to have done differently.
        messages.append(
            f"Context meter: {target_of(payload)} came back {size:,} chars "
            f"(~{size // 4:,} tokens) via {tool}, and stays resident for the rest "
            f"of the session. Cheaper next time: "
            f"{CHEAPER.get(tool, DEFAULT_CHEAPER)}."
        )

    step = entry["total"] // BUDGET_STEP
    if step >= 1 and step not in entry["steps_warned"]:
        entry["steps_warned"].append(step)
        offenders = "; ".join(
            f"{r['target']} ({r['chars']:,})" for r in entry["biggest"]
        )
        messages.append(
            f"Context meter: ~{entry['total']:,} chars (~{entry['total'] // 4:,} "
            f"tokens) of tool results ingested this session. Biggest: {offenders}. "
            f"For bulk sources, ask the user about reading them in a subagent and "
            f"returning a digest file -- the parent context then holds the findings, "
            f"not the sources."
        )

    state[session] = entry
    if len(state) > MAX_SESSIONS:
        for key in list(state)[:-MAX_SESSIONS]:
            state.pop(key, None)
    save_state(state)

    if messages:
        emit(" ".join(messages))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

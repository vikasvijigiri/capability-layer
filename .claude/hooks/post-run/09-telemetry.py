"""post-run finalizer -- one per-turn snapshot consolidating this layer's
real cost counters into a schema matching a useful subset of the Notion
"Agentic Workflows (IDE)" target's telemetry fields (see the 2026-08-20
Notion-objectives-audit doc under docs/, Gap C).

What "one run" means here
--------------------------
The target's own lifecycle records telemetry once per user task, not once
per message exchange -- closer to "this session so far" than "this one
turn" in an interactive multi-turn agent. `chain-ledger.jsonl` is genuinely
per-turn; `call-fingerprints.json` and `skill-cost.json` are session-
cumulative totals. Rather than build delta/snapshot machinery to force a
per-turn view, this writes the full cumulative-to-date snapshot every turn,
append-only -- a later reader can diff two rows for a real per-turn delta if
one is ever needed, so this does not foreclose that.

Never faking a field this harness cannot populate
---------------------------------------------------
`UNAVAILABLE_FIELDS` names every target-spec field this repo's hooks
genuinely cannot see (token counts, the active model name, API-call
boundaries, ...) and why, checked against every `load_payload()`/
`tool_input` shape this repo has ever handled. Silence would look like an
oversight; naming the gap is the deliverable Gap C's audit asked for.

The same rule applies to a counter whose *producer* is simply not present
on the current tree. `02-skill-cost.py` (the hook that writes
`skill-cost.json`) may not exist yet on every branch that carries this
file -- checked at read time (`SKILL_COST_PRODUCER.is_file()` in
`build_snapshot()`), not assumed from this module's own history: reporting
a zero-filled `skills_loaded`
when nothing ever wrote that file would look like real data. When the
producer is missing, `skills_loaded` is `None` and `"skills_loaded"` is
added to the reported `unavailable` map alongside the fixed set, with the
reason stated plainly rather than silently zeroed.

Compatible with `decisions/2026-08-07-derived-state-over-stored-state.md`:
that decision bans storing what git can already answer (workflow *state*).
Telemetry counts are not a fact about the tree -- the decision's own text
carves out exactly this category, citing the already-persisted attempt
counter as precedent.

Never blocks the turn. A reporting finalizer that could fail the Stop event
would be worse than the data it collects; every internal error is caught and
this always exits 0, regardless of what `00-dispatch.py`'s earlier steps did.

Fire it directly:

    python tools/run_hook.py post-run '{"workflow":"test","status":"success"}'
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

# parents[0] post-run, [1] hooks, [2] .claude, [3] repo root.
ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = Path(__file__).resolve().parents[1] / "state"
TELEMETRY = STATE_DIR / "telemetry.jsonl"
CALL_FINGERPRINTS = STATE_DIR / "call-fingerprints.json"
READ_COST = STATE_DIR / "read-cost.json"
AGENT_COST = STATE_DIR / "agent-cost.json"
SKILL_COST = STATE_DIR / "skill-cost.json"
SKILL_COST_PRODUCER = (Path(__file__).resolve().parents[1]
                       / "post-tool" / "02-skill-cost.py")
ENTRY_SHAPE = STATE_DIR / "last-entry-shape.json"

# Every target-spec field this repo's hooks cannot populate, and why --
# named rather than silently absent. Reused by `tools/bench.py`'s report so
# the reasons are stated once, not restated.
UNAVAILABLE_FIELDS: dict[str, str] = {
    "execution_level": "no E0-E5 router exists yet -- a separate audit gap",
    "model": "no hook payload exposes the active model name",
    "api_call_count": "not observable to a hook in this harness",
    "context_tokens": "not observable to a hook in this harness",
    "input_tokens": "not observable to a hook in this harness",
    "output_tokens": "not observable to a hook in this harness",
    "latency": "needs Start/Stop timestamp pairing per turn, not built here",
    "parallelism": "only known for planned work via parallel_groups.py, "
                   "not live-observed",
    "cache_hits": "the repeat-detector in 01-context-cost.py is a "
                  "near-miss proxy, not a true cache-hit concept",
    "cache_misses": "the repeat-detector in 01-context-cost.py is a "
                    "near-miss proxy, not a true cache-hit concept",
    "verification_level": "no discrete per-run counter exists yet",
    "retries": "no discrete per-run counter exists yet",
    "escalations": "no discrete per-run counter exists yet",
    "success": "no signal exists; needs human or verification-result input",
    "quality_signal": "no signal exists; needs human or verification-result "
                       "input",
}


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _load_module(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _chain_facts() -> dict:
    chain = _load_module("tools/chain.py", "chain_for_telemetry")
    if chain is None:
        return {}
    try:
        facts = chain.gather(ROOT)
    except Exception:
        return {}
    return {"state": facts.get("state"), "slug": facts.get("slug"),
            "fingerprint": facts.get("fingerprint"),
            "progress": facts.get("progress")}


def build_snapshot() -> dict:
    call_totals = _load_json(CALL_FINGERPRINTS).get("_totals") or {}
    entry_shape = _load_json(ENTRY_SHAPE)
    unavailable = dict(UNAVAILABLE_FIELDS)

    skills_loaded: dict | None
    if SKILL_COST_PRODUCER.is_file():
        skill_totals = _load_json(SKILL_COST)
        skills_loaded = {
            "calls": skill_totals.get("calls", 0),
            "chars": skill_totals.get("chars", 0),
            "unattributed": skill_totals.get("unattributed", 0),
        }
    else:
        skills_loaded = None
        unavailable["skills_loaded"] = (
            "02-skill-cost.py, the counter's producer, is not present on "
            "this tree -- it ships on a separate unit, not yet merged here"
        )

    read_totals = _load_json(READ_COST)
    agent_totals = _load_json(AGENT_COST)
    calls = call_totals.get("calls", 0)
    repeats = call_totals.get("repeats", 0)

    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "run_scope": "session-cumulative",
        "chain": _chain_facts(),
        "tools_called": {
            "calls": calls,
            "chars": call_totals.get("chars", 0),
            "repeats": repeats,
        },
        "skills_loaded": skills_loaded,
        "task_type": entry_shape.get("key"),
        # Proxy for the spec's `context_tokens` -- see 04-read-cost.py's
        # docstring. Not the real field, which stays in `unavailable` below.
        "context_read": {
            "calls": read_totals.get("calls", 0),
            "chars": read_totals.get("chars", 0),
        },
        "agents_spawned": {
            "calls": agent_totals.get("calls", 0),
            "by_type": agent_totals.get("by_type", {}),
        },
        # Spec's own term (§21 "Duplicate-operation rate"); pure arithmetic
        # over tools_called, which already tracks calls/repeats.
        "duplicate_rate": (repeats / calls) if calls else 0.0,
        "unavailable": unavailable,
    }


def main() -> int:
    try:
        load_payload()  # drains stdin/HOOK_PAYLOAD per the shared contract; unused
        snapshot = build_snapshot()
        TELEMETRY.parent.mkdir(parents=True, exist_ok=True)
        with TELEMETRY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(snapshot) + "\n")
    except Exception:
        # A reporting finalizer must never fail the turn it is reporting on.
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

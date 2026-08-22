"""telemetry -- one per-turn snapshot consolidating this layer's
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

    python tools/run_hook.py telemetry '{"workflow":"test","status":"success"}'
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

# parents[0] telemetry, [1] hooks, [2] .claude, [3] repo root.
ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = Path(__file__).resolve().parents[1] / "state"
TELEMETRY = STATE_DIR / "telemetry.jsonl"
CALL_FINGERPRINTS = STATE_DIR / "call-fingerprints.json"
READ_COST = STATE_DIR / "read-cost.json"
AGENT_COST = STATE_DIR / "agent-cost.json"
SKILL_COST = STATE_DIR / "skill-cost.json"
SKILL_COST_PRODUCER = (Path(__file__).resolve().parents[1]
                       / "context-budget" / "02-skill-cost.py")
ENTRY_SHAPE = STATE_DIR / "last-entry-shape.json"
TOOL_COST = STATE_DIR / "tool-cost.json"
HUMAN_COST = STATE_DIR / "human-cost.json"
TURN_TIMER = STATE_DIR / "turn-timer.json"

# The Notion spec SS21's own named field count -- run_id, task_type,
# execution_level, model, skills_loaded, agents_spawned, tools_called,
# api_call_count, context_tokens, input_tokens, output_tokens, latency,
# parallelism, cache_hits, cache_misses, repeated_operations_avoided,
# verification_level, retries, escalations, success, quality_signal.
# `tools/bench.py:schema_coverage()` (objective 22) computes its ratio
# against this count, imported rather than re-declared, so a field added
# here is reflected there without a second edit.
SPEC_FIELD_COUNT = 21

# Every target-spec field this repo's hooks cannot populate, and why --
# named rather than silently absent. Reused by `tools/bench.py`'s report so
# the reasons are stated once, not restated.
UNAVAILABLE_FIELDS: dict[str, str] = {
    "model": "no hook payload exposes the active model name",
    "context_tokens": "not observable to a hook in this harness",
    "input_tokens": "not observable to a hook in this harness",
    "output_tokens": "not observable to a hook in this harness",
    "escalations": "folded into retries.rung's block/retreat outcomes -- "
                   "no separate counter; see objective 24's "
                   "local_repair_ratio() in tools/bench.py",
    "parallelism": "only known for planned work via parallel_groups.py, "
                   "not live-observed",
    "cache_hits": "the repeat-detector in 01-context-cost.py is a "
                  "near-miss proxy, not a true cache-hit concept",
    "cache_misses": "the repeat-detector in 01-context-cost.py is a "
                    "near-miss proxy, not a true cache-hit concept",
    "verification_level": "no discrete per-run counter exists yet",
    "success": "no signal exists; needs human or verification-result input",
    "quality_signal": "no signal exists; needs human or verification-result "
                       "input",
}


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _tail_last_json_line(path: Path, max_bytes: int = 8192) -> dict:
    """The last JSON object in an append-only JSONL file, or {} -- never a
    full-file read. `telemetry.jsonl` is append-only and never truncated (see
    module docstring), so it only grows over a repo's lifetime; a bounded tail
    read keeps this hook's own cost from growing with it."""
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            fh.seek(max(0, size - max_bytes))
            chunk = fh.read()
        lines = [ln for ln in chunk.decode("utf-8", errors="ignore").split("\n")
                 if ln.strip()]
        if not lines:
            return {}
        return json.loads(lines[-1])
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


def _turn_latency() -> tuple[float | None, str | None]:
    """Seconds since 02-turn-timer.py's last `UserPromptSubmit`, or a reason.

    `None` for the first turn of a session (the timer has never fired) or if
    the state file cannot be read -- both real absences, not a guessed 0.0.
    """
    timer = _load_json(TURN_TIMER)
    started_at = timer.get("started_at")
    if not isinstance(started_at, (int, float)):
        return None, ("02-turn-timer.py has not fired yet this session -- "
                       "no start timestamp recorded")
    return time.time() - started_at, None


def _retry_facts(slug: str | None) -> dict:
    """attempts/max_attempts/failure_class/rung, surfaced -- never invented.

    `tools/resume.py:gather_facts()` already computes the first three;
    `tools/loop.py:rung()` already turns them into the same repair/restore/
    rebase/retreat/block verdict its own CLI prints. Nothing here recomputes
    that logic, it reads what both tools already own -- same "surface, don't
    invent" move as `duplicate_rate` (2026-08-21, three-spec-metrics).

    Offline by default, matching `tools/chain.py:gather(offline=True)`'s own
    precedent: `Stop` fires every turn, and `gather_facts`'s `gh pr list`
    calls must never tax it.
    """
    empty = {"attempts": 0, "max_attempts": 0, "failure_class": None,
              "rung": None}
    loop_mod = _load_module("tools/loop.py", "loop_for_telemetry")
    if loop_mod is None:
        return empty
    resume_mod = getattr(loop_mod, "_rs", None)
    if resume_mod is None:
        return empty
    resume_mod._gh_json = lambda *a, **k: None
    try:
        facts = resume_mod.gather_facts(ROOT, slug)
        state = resume_mod.derive_state(facts)
        ledger = resume_mod.read_ledger(ROOT, facts.get("slug"))
    except Exception:
        return empty

    result = {
        "attempts": facts.get("attempts", 0),
        "max_attempts": facts.get("max_attempts", 0),
        "failure_class": facts.get("failure_class"),
        "rung": None,
    }
    if state in ("REPAIR", "BLOCKED"):
        try:
            detail = ledger.get("detail", "") or ""
            kind = ledger.get("failure_class") or loop_mod.classify_failure(detail)[0]
            budget = loop_mod.failure_budget(kind)
            sha = loop_mod.green_sha(ROOT, facts.get("slug"))
            result["rung"] = loop_mod.rung(
                kind, int(facts.get("attempts", 0)), budget,
                restored=bool(ledger.get("restored")), has_green=bool(sha),
            )
        except Exception:
            pass  # attempts/max_attempts/failure_class are still real; rung alone is not
    return result


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


def _actual_execution_level(skills_loaded: dict | None, agent_totals: dict,
                             tool_calls: int) -> str | None:
    """The E0-E5 level this turn actually reached, from real counters --
    prompt-intake/01-entry-classifier.py's `execution_level_predicted` is a
    forecast made before the turn ran; this is what happened, so the two
    together make prediction accuracy measurable (objective 30) without a
    second mechanism. `None` when skills_loaded's own producer is absent,
    matching that field's own unavailability rather than guessing.
    """
    if skills_loaded is None:
        return None
    agent_calls = agent_totals.get("calls", 0)
    skill_calls = skills_loaded.get("calls", 0)
    if agent_calls > 4:
        return "E5"
    if agent_calls >= 2:
        return "E4"
    if agent_calls == 1:
        return "E3"
    if skill_calls >= 1:
        return "E2" if tool_calls > 2 else "E1"
    return "E1" if tool_calls > 0 else "E0"


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
    tool_totals = _load_json(TOOL_COST)
    human_totals = _load_json(HUMAN_COST)
    calls = call_totals.get("calls", 0)
    repeats = call_totals.get("repeats", 0)

    chain = _chain_facts()
    turn_latency_seconds, latency_reason = _turn_latency()
    if latency_reason:
        unavailable["turn_latency_seconds"] = latency_reason

    # `run_id`: not the target's strict "one user task" boundary -- this
    # repo has no such thing (see module docstring's "What 'one run' means
    # here"). What it IS: a real identifier for which unit of work, at what
    # tree state, `chain.py` already computes as slug+fingerprint. Naming it
    # `run_id` exposes that existing identifier rather than inventing a new
    # concept; a future reader should not assume it changes per-invocation.
    run_slug = chain.get("slug")
    run_fp = chain.get("fingerprint")
    if run_slug and run_fp:
        run_id = f"{run_slug}:{run_fp}"
    else:
        run_id = None
        unavailable["run_id"] = (
            "no active chain state this turn -- slug and/or fingerprint "
            "unresolved; see tools/chain.py"
        )

    # `execution_level.actual` must reflect THIS turn, not the session so
    # far -- `_actual_execution_level()` is unit-tested against per-turn-
    # shaped inputs (tools/test_bench.py), so the cumulative totals above
    # are diffed against the previous row before being passed in. Read
    # before this row is appended (main() opens TELEMETRY for append only
    # after build_snapshot() returns), so `previous` never sees this turn.
    previous = _tail_last_json_line(TELEMETRY)
    prev_skill_calls = (previous.get("skills_loaded") or {}).get("calls", 0)
    prev_agent_calls = (previous.get("agents_spawned") or {}).get("calls", 0)
    prev_tool_calls = (previous.get("api_calls") or {}).get("calls", 0)
    agent_calls_now = agent_totals.get("calls", 0)
    tool_calls_now = tool_totals.get("calls", 0)
    # max(0, ...): a reset state file (e.g. .claude/hooks/state/ cleared
    # between turns) would otherwise produce a negative delta, which is not
    # a real negative count.
    delta_agent_calls = max(0, agent_calls_now - prev_agent_calls)
    delta_tool_calls = max(0, tool_calls_now - prev_tool_calls)
    if skills_loaded is None:
        skills_loaded_delta = None
    else:
        delta_skill_calls = max(
            0, skills_loaded.get("calls", 0) - prev_skill_calls)
        skills_loaded_delta = {"calls": delta_skill_calls}

    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "run_scope": "session-cumulative",
        "run_id": run_id,
        "chain": chain,
        "tools_called": {
            "calls": calls,
            "chars": call_totals.get("chars", 0),
            "repeats": repeats,
        },
        "skills_loaded": skills_loaded,
        "task_type": entry_shape.get("key"),
        "execution_level": {
            "predicted": entry_shape.get("execution_level_predicted"),
            "actual": _actual_execution_level(
                skills_loaded_delta,
                {"calls": delta_agent_calls},
                delta_tool_calls),
        },
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
        # Total across every tool name (06-tool-cost.py's matcher "*"), not
        # the narrower Bash/PowerShell-only tools_called above.
        "api_calls": {
            "calls": tool_totals.get("calls", 0),
            "by_tool": tool_totals.get("by_tool", {}),
        },
        "turn_latency_seconds": turn_latency_seconds,
        # Raw counts only -- no invented per-task/per-session denominator,
        # same as agents_spawned's own already-shipped shape.
        "human_interventions": {
            "calls": human_totals.get("calls", 0),
            "by_tool": human_totals.get("by_tool", {}),
        },
        "retries": _retry_facts(chain.get("slug")),
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

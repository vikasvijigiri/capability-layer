#!/usr/bin/env python3
"""What this layer costs per session and per turn, measured rather than claimed.

Every optimisation of this layer so far has been argued from a number somebody
remembered. Two of them were wrong: the full tier was quoted as ~196s in two
files long after it stopped being true, and `tools/` was called bloat when none
of it enters context at all. This prints the numbers instead.

    python tools/bench.py              # measure and print
    python tools/bench.py --save       # record the current run as the baseline
    python tools/bench.py --full       # include the full tier (minutes)

With a baseline recorded, later runs print the delta, so "this made it cheaper"
is a comparison a reader can re-run rather than a claim they have to take.

Four costs, and they are paid on different clocks -- which is the whole point of
separating them. A byte in `CLAUDE.md` is paid once per session; a byte of skill
description is paid on *every turn*, because the listing is re-injected each
time; a second of the fast tier is paid at the end of every turn that
checkpoints. Optimising the wrong one of these is how effort goes nowhere.

Token figures are bytes/4 and are labelled estimates. A real tokeniser would be
a dependency this repo does not otherwise need, and the ratio between two runs
-- which is what this tool is for -- is unaffected by the constant.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / ".claude" / "hooks" / "state" / "bench-baseline.json"
TELEMETRY = ROOT / ".claude" / "hooks" / "state" / "telemetry.jsonl"


def _load_module(rel: str, name: str):
    """Same seam `.claude/hooks/telemetry/09-telemetry.py` and `tools/loop.py`
    already use -- one file owns a constant, everyone else imports it rather
    than re-declaring the number."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_TELEMETRY_MOD = None


def _telemetry_module():
    """Cached load of 09-telemetry.py -- its own top-level `sys.path.insert`
    is a real side effect of `_load_module()`, not just a constant read, so
    a caller reloading it on every call grows `sys.path` by one duplicate
    entry each time (measured: 2 loads -> 2 identical entries). Loaded once
    per process instead."""
    global _TELEMETRY_MOD
    if _TELEMETRY_MOD is None:
        _TELEMETRY_MOD = _load_module(
            ".claude/hooks/telemetry/09-telemetry.py", "telemetry_for_bench")
    return _TELEMETRY_MOD

# Loaded once when a session opens.
SESSION_FILES = ("CLAUDE.md", "CLAUDE.local.md")
RULES_DIR = ROOT / ".claude" / "rules"

DESC_RE = re.compile(r"^description:\s*(.*)$", re.M)
WHEN_RE = re.compile(r"^when_to_use:\s*(.*)$", re.M)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def session_preamble() -> int:
    """Bytes loaded once per session: the bootloader plus the standing rules."""
    total = sum(len(_read(ROOT / name)) for name in SESSION_FILES)
    if RULES_DIR.is_dir():
        total += sum(len(_read(p)) for p in sorted(RULES_DIR.glob("*.md")))
    return total


def per_turn_descriptions() -> int:
    """Bytes re-injected on EVERY turn: the skill, command and agent listings.

    Only the frontmatter fields that reach the listing count. A skill's body is
    read after it is selected and costs nothing until then, which is exactly why
    moving prose out of `description:` and into the body is worth doing and
    moving it out of the file entirely is not.
    """
    total = 0
    for skill in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        head = FRONTMATTER_RE.match(_read(skill))
        if not head:
            continue
        block = head.group(1)
        for pattern in (DESC_RE, WHEN_RE):
            found = pattern.search(block)
            total += len(found.group(1)) if found else 0
    for folder in ("commands", "agents"):
        for doc in sorted((ROOT / ".claude" / folder).glob("*.md")):
            text = _read(doc)
            # `disable-model-invocation: true` keeps the entry OUT of the skill
            # listing entirely -- it is how a user-only command stops costing
            # context. Counting it anyway made this tool report no change when
            # eleven commands were switched to user-only on 2026-08-15, which is
            # the instrument disagreeing with the thing it measures.
            if re.search(r"^disable-model-invocation:\s*true\b", text, re.M):
                continue
            found = DESC_RE.search(text)
            total += len(found.group(1).splitlines()[0]) if found else 0
    return total


def session_start() -> tuple[int, float]:
    """(bytes, seconds) the SessionStart hooks emit into every new session."""
    folder = ROOT / ".claude" / "hooks" / "session-init"
    if not folder.is_dir():
        return 0, 0.0
    env = {**os.environ, "PYTHONIOENCODING": "utf-8",
           "HOOK_PAYLOAD": json.dumps({"hook_event_name": "SessionStart",
                                       "cwd": str(ROOT)})}
    chars, started = 0, time.monotonic()
    for script in sorted(folder.glob("*.py")):
        try:
            proc = subprocess.run(  # noqa: S603
                ["python", str(script)], cwd=str(ROOT), capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=120,
                env=env,
            )
        except Exception as exc:  # noqa: BLE001
            # Named, never swallowed. A hook that cannot run contributes zero
            # bytes, which is indistinguishable from a hook that ran and printed
            # nothing -- and this tool exists to make costs visible, so a
            # measurement with a hole in it must say where the hole is.
            print(f"  ! {script.name} could not run: "
                  f"{type(exc).__name__} -- its cost is missing below")
            continue
        chars += len(proc.stdout or "")
    return chars, time.monotonic() - started


def session_calls() -> tuple[int, int, int]:
    """(shell calls, chars, repeats) this session, from the post-tool counter.

    `Agentic Workflows (IDE)` section 21 requires `tools_called` and
    `api_call_count` per run; without them objectives 4 and 5 can be asserted
    and never graded. Zeros mean the hook has not fired yet in this session,
    which is different from a session that made no calls -- the caller says
    which, rather than this function guessing.
    """
    state = (ROOT / ".claude" / "hooks" / "state" / "call-fingerprints.json")
    try:
        totals = json.loads(state.read_text(encoding="utf-8")).get("_totals") or {}
    except (OSError, ValueError):
        return 0, 0, 0
    return (int(totals.get("calls", 0)), int(totals.get("chars", 0)),
            int(totals.get("repeats", 0)))


def total_tool_calls() -> tuple[int, int]:
    """(total calls, distinct tool names) this session, from
    `post-tool/06-tool-cost.py`'s counter.

    `session_calls()` above only ever saw Bash/PowerShell -- every `Write`,
    `Edit`, `Grep`, `Glob`, `WebFetch`, `WebSearch`, and `mcp__*` tool call
    was invisible to it. This is the spec's own `api_call_count` (objective
    4), counted across every tool name, not one slice of them. Zero means
    the hook has not fired yet, same convention as its neighbours.
    """
    state = (ROOT / ".claude" / "hooks" / "state" / "tool-cost.json")
    try:
        totals = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0, 0
    return int(totals.get("calls", 0)), len(totals.get("by_tool") or {})


def schema_coverage() -> tuple[float | None, list[str], bool]:
    """(coverage ratio, missing field names, trace-completeness) -- objective
    22 (observable and auditable), from the latest `telemetry.jsonl` row.

    `coverage_ratio = (SPEC_FIELD_COUNT - len(unavailable)) / SPEC_FIELD_COUNT`
    against the Notion spec SS21's own 21 named fields, `SPEC_FIELD_COUNT`
    imported from `09-telemetry.py` rather than re-declared here (one place
    owns the count, so a name added to `UNAVAILABLE_FIELDS` there is
    reflected here without a second edit). `trace_complete` checks
    `chain.fingerprint`, never `chain.slug` -- slug is legitimately `None`
    for a turn with no active plan, fingerprint is always computable. `None`
    coverage means no telemetry row exists yet, not zero coverage.
    """
    try:
        lines = TELEMETRY.read_text(encoding="utf-8").splitlines()
        row = json.loads(lines[-1])
    except (OSError, ValueError, IndexError):
        return None, [], False
    spec_field_count = _telemetry_module().SPEC_FIELD_COUNT
    unavailable = row.get("unavailable") or {}
    ratio = (spec_field_count - len(unavailable)) / spec_field_count
    trace_complete = bool((row.get("chain") or {}).get("fingerprint"))
    return ratio, list(unavailable.keys()), trace_complete


def local_repair_ratio() -> tuple[float | None, dict[str, int]]:
    """(ratio, counts_by_rung) -- objective 24 (self-adapting and
    self-healing), aggregated over the whole `telemetry.jsonl` history.

    "Detect, diagnose locally, repair when safe... escalate only when
    current capability is insufficient" is `tools/loop.py:rung()`'s own
    repair/restore/rebase/retreat/block ladder, already surfaced into every
    telemetry row's `retries.rung` field. `ratio = (repair + restore) /
    total`, `None` when nothing has ever entered the ladder.

    **Deduplicated by incident, not by turn.** `telemetry.jsonl` appends one
    row per `Stop` -- every turn -- so counting rows directly turn-weights
    the ratio: one incident that takes 20 turns to resolve would outweigh 19
    incidents resolved in one turn each. The identity of "one thing the
    ladder was asked to fix" is `(chain.slug, retries.attempts)` -- slug
    alone is not unique across a session that worked on more than one unit,
    and attempts alone is not unique across units that both reached the same
    attempt count. Last-seen rung wins for a given key, since it is that
    attempt's current verdict.

    A low ratio is not automatically bad -- objective 1 (minimal human
    interference) and objective 24 pull against each other at the margin.
    This function reports the ratio; it does not judge it.
    """
    try:
        lines = TELEMETRY.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, {}
    incidents: dict[tuple[str | None, int | None], str] = {}
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        retries = row.get("retries") or {}
        rung = retries.get("rung")
        if rung is None:
            continue
        key = ((row.get("chain") or {}).get("slug"), retries.get("attempts"))
        incidents[key] = rung  # last-seen wins for this (slug, attempts) pair
    if not incidents:
        return None, {}
    counts: dict[str, int] = {}
    for rung in incidents.values():
        counts[rung] = counts.get(rung, 0) + 1
    total = sum(counts.values())
    ratio = (counts.get("repair", 0) + counts.get("restore", 0)) / total
    return ratio, counts


def skill_body_cost() -> tuple[int, int, int]:
    """(skill invocations, SKILL.md chars loaded, unattributed) this session,
    from `context-budget/02-skill-cost.py`'s counter.

    A full chain run loads a full `SKILL.md` body per stage, on top of the
    per-turn listing `session_calls()`'s neighbour rows already measure --
    nothing counted this before. Zeros mean the hook has not fired yet, same
    convention as `session_calls()`.
    """
    state = (ROOT / ".claude" / "hooks" / "state" / "skill-cost.json")
    try:
        totals = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0, 0, 0
    return (int(totals.get("calls", 0)), int(totals.get("chars", 0)),
            int(totals.get("unattributed", 0)))


def tier(name: str) -> float:
    """Wall seconds for one check tier. Returns -1.0 when it could not run."""
    args = ["python", "tools/run_checks.py", "--tier", name]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    started = time.monotonic()
    try:
        subprocess.run(args, cwd=str(ROOT), capture_output=True,  # noqa: S603
                       timeout=1800, env=env)
    except Exception:  # noqa: BLE001
        return -1.0
    return time.monotonic() - started


def measure(full: bool) -> dict:
    start_chars, start_secs = session_start()
    data = {
        "session_preamble_chars": session_preamble(),
        "per_turn_description_chars": per_turn_descriptions(),
        "session_start_chars": start_chars,
        "session_start_seconds": round(start_secs, 2),
        "fast_tier_seconds": round(tier("fast"), 1),
    }
    if full:
        data["full_tier_seconds"] = round(tier("all"), 1)
    return data


ROWS = [
    ("session_preamble_chars", "CLAUDE.md + rules", "once per session", True),
    ("session_start_chars", "SessionStart output", "once per session", True),
    ("per_turn_description_chars", "skill/cmd/agent listing", "EVERY TURN", True),
    ("session_start_seconds", "SessionStart hooks", "once per session", False),
    ("fast_tier_seconds", "fast tier", "every checkpointing turn", False),
    ("full_tier_seconds", "full tier", "once before delivery", False),
]


TIMING_CAVEAT = (
    "Character counts are exact. The SECONDS are not: a fast tier's own\n"
    "measurement can drift by 2x or more within one hour on an unchanged\n"
    "tree, because the suites are disk-bound and the machine's other work\n"
    "moves them. Do not\n"
    "compare a second-figure across runs taken at different times -- to compare\n"
    "two configurations, run them INTERLEAVED (a, b, a, b) so drift hits both."
)


def render(now: dict, was: dict | None) -> None:
    print(f"{'cost':28} {'value':>12} {'est. tokens':>12}  {'vs baseline':>13}  paid")
    print("-" * 88)
    for key, label, cadence, is_chars in ROWS:
        if key not in now:
            continue
        value = now[key]
        shown = f"{value:,} ch" if is_chars else f"{value}s"
        tokens = f"~{value // 4:,}" if is_chars else ""
        delta = ""
        if was and key in was and was[key]:
            change = (value - was[key]) / was[key] * 100
            delta = f"{change:+.0f}%"
        print(f"{label:28} {shown:>12} {tokens:>12}  {delta:>13}  {cadence}")
    calls, call_chars, repeats = session_calls()
    if calls:
        pct = repeats * 100 // calls
        print(f"\nthis session's shell calls: {calls:,}  "
              f"({call_chars:,} chars of input, ~{call_chars // 4:,} tok)  "
              f"repeats: {repeats:,} ({pct}%)")
        print(f"  duplicate-operation rate: {pct}% ({repeats:,}/{calls:,}) "
              f"-- the spec's own §21 term for this number.")
        print("  Objective 5 is graded from this. A repeat is a call whose "
              "answer\n  was already in context -- reuse before retrieve.")
    else:
        print("\nthis session's shell calls: not yet recorded -- the post-tool "
              "counter\n  writes on the first shell call of a session.")

    total_calls, distinct_tools = total_tool_calls()
    if total_calls:
        print(f"\nthis session's total tool calls (every tool, spec's "
              f"api_call_count): {total_calls:,}  "
              f"across {distinct_tools} distinct tool name(s)")
        print("  Objective 4 is graded from this -- the shell-calls line above "
              "is Bash/PowerShell only.")
    else:
        print("\nthis session's total tool calls: not yet recorded -- the "
              "post-tool counter\n  writes on the first tool call of a "
              "session.")

    skill_calls, skill_chars, unattributed = skill_body_cost()
    if skill_calls:
        note = f"  ({unattributed:,} unattributed)" if unattributed else ""
        print(f"\nthis session's skill-body loads: {skill_calls:,}  "
              f"({skill_chars:,} chars, ~{skill_chars // 4:,} tok){note}")
        print("  upper bound -- does not know which calls Claude Code's own "
              "dedup already served for free")
    else:
        print("\nthis session's skill-body loads: not yet recorded -- the "
              "post-tool counter\n  writes on the first Skill-tool "
              "invocation of a session.")

    coverage, missing, trace_complete = schema_coverage()
    if coverage is None:
        print("\nobjective 22 (schema coverage): not yet recorded -- no "
              "telemetry row exists yet this session.")
    else:
        print(f"\nobjective 22 (schema coverage): {coverage:.0%}  "
              f"missing: {missing or 'none'}  trace_complete: {trace_complete}")

    repair_ratio, rung_counts = local_repair_ratio()
    if repair_ratio is None:
        print("\nobjective 24 (local-repair ratio): not yet recorded -- no "
              "turn has entered the repair ladder this session.")
    else:
        print(f"\nobjective 24 (local-repair ratio): {repair_ratio:.0%}  "
              f"by rung: {rung_counts}")

    print("\n" + TIMING_CAVEAT)
    if was is None:
        print("\nNo baseline recorded. `python tools/bench.py --save` writes one.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true",
                        help="record this run as the baseline to compare against")
    parser.add_argument("--full", action="store_true",
                        help="also time the full tier; takes minutes")
    args = parser.parse_args()

    now = measure(args.full)
    was = None
    if BASELINE.is_file():
        try:
            was = json.loads(BASELINE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            was = None

    render(now, was)

    if args.save:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"\nbaseline written to {BASELINE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

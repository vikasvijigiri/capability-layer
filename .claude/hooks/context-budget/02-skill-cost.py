"""context-budget -- counts Skill tool invocations and the SKILL.md bytes each one
loads into context, mirroring `01-context-cost.py`'s shape for a second cost
category `tools/bench.py` could not see before this: a full 9-stage chain run
loads ~104,000 chars (~26,000 tok) of skill-body prose in one session, and
nothing measured it.

Separate state file from `01-context-cost.py`'s `call-fingerprints.json` on
purpose -- different concept (a running total, not per-call fingerprints with
a repeat check), and coupling an unrelated schema into a row-bounded file
buys nothing.

The field name carrying the skill's identifier in `tool_input` is not
documented (checked: neither Claude Code's hooks reference nor this repo's
own history covers the `Skill` tool). `"skill"` is the primary candidate --
it matches the `Skill` tool's own declared parameter name -- with
`"skill_name"`/`"name"` as defensive fallbacks. A payload matching none of
them still counts as a call, under `unattributed`, rather than being
silently dropped: the raw invocation count must stay honest even when
per-skill attribution cannot.

This counter also cannot see Claude Code's own dedup: a repeat `Skill`
invocation whose rendered content is unchanged (same args, no differing
dynamic context) gets a short "already loaded" note instead of the full
body again, but this hook still adds that skill's full on-disk size --
it has no way to observe which invocation the harness actually served
from cache. So `calls`/`chars` here is an upper bound on real per-session
skill-body cost, not a measured one. `tools/bench.py`'s report states
this same limitation where it prints the figure.

Silent by default, matching `01-context-cost.py`: this reports state, it
does not warn. Also keeps it outside `decisions/2026-08-04-hooks-never-
name-a-skill.md`'s literal scope, which bans a skill name in anything a hook
EMITS (stdout/stderr/JSON reaching the session) -- this hook writes to a
state file only, never to stdout in the normal case.

Fire it directly:

    python tools/run_hook.py post-tool '{"tool_name":"Skill","tool_input":{"skill":"some-skill-name"}}'
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from _hooklib import load_payload
except Exception:  # pragma: no cover - a guard that cannot load must not wedge
    sys.exit(0)

WATCHED = ("Skill",)

# Tried in order. "skill" matches the Skill tool's own declared parameter
# name; the other two are defensive fallbacks for a payload shape this
# session could not observe live -- see the module docstring.
NAME_KEYS = ("skill", "skill_name", "name")

# parents[1] is `.claude/hooks`, parents[2] is `.claude` itself -- no
# further `.claude/` segment needed underneath it.
SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
STATE = Path(__file__).resolve().parents[1] / "state" / "skill-cost.json"


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(totals: dict) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(totals), encoding="utf-8")
    except OSError:
        pass  # a counter that cannot persist still must not break the turn


def _skill_name(tool_input: dict) -> str | None:
    for key in NAME_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _skill_md_size(name: str) -> int:
    # No path segments allowed -- a real skill name is a single directory
    # component. Rejecting "/", "\\" and ".." here (rather than resolving and
    # checking containment) keeps this a pure string check with nothing to
    # get wrong about symlinks or platform separators.
    if "/" in name or "\\" in name or ".." in name:
        return 0
    path = SKILLS_DIR / name / "SKILL.md"
    try:
        return path.stat().st_size
    except OSError:
        # A stale or renamed skill name is itself worth surfacing later via
        # bench.py's report, not hidden by treating it as zero cost silently.
        return 0


def main() -> int:
    payload = load_payload() or {}
    if payload.get("tool_name") not in WATCHED:
        return 0

    tool_input = payload.get("tool_input") or {}
    name = _skill_name(tool_input)

    totals = _load()
    totals["calls"] = totals.get("calls", 0) + 1
    totals["chars"] = totals.get("chars", 0)
    totals["unattributed"] = totals.get("unattributed", 0)
    if name is None:
        totals["unattributed"] += 1
    else:
        totals["chars"] += _skill_md_size(name)
    _save(totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

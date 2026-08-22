#!/usr/bin/env python3
"""Objective 11 (world-class engineering) -- instrumented-surface coverage.

A floor, explicitly not the objective: live-wired hooks and `tools/*.py`
source files with a resolving entry in `.claude/project-checks.json`'s
`test` array, divided by all of them. Proves the objective is being missed;
never proves it is met (`docs/specs/2026-08-21-qualitative-objective-
metrics.md`'s own framing for this instrument).

Deliberately uses array-membership-by-file-stem, not `test_map` resolution:
`test_map` carries catch-all globs (`.claude/hooks/**` -> `test_hooks.py`,
`.claude/skills/**` -> `test_process_router.py`) that would make nearly
every file trivially "covered" and hide the real gap this instrument exists
to report -- confirmed live this session: `01-context-cost.py` had zero
dedicated test coverage despite already resolving through that catch-all.

Report only -- exits 0 regardless.

Run: python tools/test_instrumented_surface.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / ".claude" / "settings.json"
PROJECT_CHECKS = ROOT / ".claude" / "project-checks.json"
TOOLS_DIR = ROOT / "tools"


def discover_hooks() -> list[Path]:
    """Every registered command hook, from `settings.json` -- same discovery
    pattern as `tools/test_hook_conformance.py`, repeated rather than
    imported for the same additive-scope reason recorded there."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    found: list[Path] = []
    seen: set[Path] = set()
    for groups in settings.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                match = re.search(r"\.claude/hooks/([^\"']+\.py)", hook.get("command", ""))
                if not match:
                    continue
                path = ROOT / ".claude" / "hooks" / Path(match.group(1))
                if path.is_file() and path not in seen:
                    seen.add(path)
                    found.append(path)
    return found


NUMERIC_PREFIX_RE = re.compile(r"^\d+-")


def normalize(stem: str) -> str:
    """`01-context-cost` -> `context_cost`; `bench` -> `bench` -- matches
    this repo's own hook-to-test naming convention (numeric prefix dropped,
    hyphens become underscores, e.g. `01-context-cost.py` <-> `test_context_
    cost.py`, confirmed live against the actual `tools/test_context_cost.py`
    added this session)."""
    return NUMERIC_PREFIX_RE.sub("", stem).replace("-", "_")


def is_covered(stem: str, test_array_text: str) -> bool:
    """Is `stem` (normalized) referenced by name anywhere in the `test`
    array's command strings? Substring match, not exact equality -- a
    source stem is covered whether the test is named `test_<stem>.py`
    (the common case) or merely contains the stem as a substring."""
    needle = normalize(stem)
    return needle in test_array_text


def main() -> int:
    checks = json.loads(PROJECT_CHECKS.read_text(encoding="utf-8"))
    test_array = checks.get("test", [])
    if test_array is False:
        test_array = []
    test_array_text = normalize("\n".join(test_array))

    hooks = discover_hooks()
    tool_sources = sorted(p for p in TOOLS_DIR.glob("*.py") if not p.name.startswith("test_"))

    surface = [(p, p.stem) for p in hooks] + [(p, p.stem) for p in tool_sources]
    misses = []
    for path, stem in surface:
        if not is_covered(stem, test_array_text):
            misses.append(path.relative_to(ROOT).as_posix())

    total = len(surface)
    n_covered = total - len(misses)
    print(f"objective 11 (instrumented-surface coverage): {n_covered}/{total} "
          f"({len(hooks)} live-wired hook(s), {len(tool_sources)} tools/*.py source(s))")
    for m in misses:
        print(f"  MISS: {m} -- no test_*.py naming this stem in project-checks.json's test array")
    print("\nA floor, not the objective -- this can prove a miss, never prove "
          "coverage is adequate. Report only, exits 0 regardless.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

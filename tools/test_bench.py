#!/usr/bin/env python3
"""Tests for tools/bench.py's telemetry-derived report functions.

Each function here reads a real repository file (`telemetry.jsonl`, gitignored
and session-specific) and must never assume it exists or is well-formed --
"not yet recorded" is a real, honest answer, not a bug. Every seeded case
proves the function can actually detect the violation it claims to detect,
per this repository's Article II: a check nobody has broken on purpose is a
check nobody has verified can fail.

Run: python tools/test_bench.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bench = load("tools/bench.py", "bench_for_test")
telemetry_mod = load(".claude/hooks/post-run/09-telemetry.py", "telemetry_for_test")
SPEC_FIELD_COUNT = telemetry_mod.SPEC_FIELD_COUNT


def with_telemetry(rows: list[dict]):
    """Point bench.TELEMETRY at a throwaway file for the duration of a case."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)  # mkstemp's own handle must close before Windows allows unlink
    tmp = Path(path)
    tmp.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""),
                    encoding="utf-8")
    original = bench.TELEMETRY
    bench.TELEMETRY = tmp
    return tmp, original


def restore(tmp: Path, original: Path) -> None:
    bench.TELEMETRY = original
    tmp.unlink(missing_ok=True)


# --- schema_coverage() (objective 22) ----------------------------------------

# A fixture with 3 of SPEC_FIELD_COUNT fields unavailable must report exactly
# (SPEC_FIELD_COUNT - 3) / SPEC_FIELD_COUNT -- not a rounded or off-by-one value.
_unavailable_3 = {f"field{i}": "reason" for i in range(3)}
_row = {"unavailable": _unavailable_3, "chain": {"fingerprint": "abc123"}}
tmp, orig = with_telemetry([_row])
ratio, missing, trace_complete = bench.schema_coverage()
restore(tmp, orig)
_want_ratio = (SPEC_FIELD_COUNT - 3) / SPEC_FIELD_COUNT
check("schema_coverage() computes the exact expected ratio against the real "
      "SPEC_FIELD_COUNT, not a hardcoded local recompute",
      ratio is not None and abs(ratio - _want_ratio) < 1e-9,
      f"got {ratio!r}, want {_want_ratio!r} (SPEC_FIELD_COUNT={SPEC_FIELD_COUNT})")
check("schema_coverage() reports the missing field names",
      sorted(missing) == sorted(_unavailable_3), str(missing))
check("schema_coverage() reports trace_complete True when chain.fingerprint "
      "is present",
      trace_complete is True)

# chain.fingerprint absent -> trace_complete must be False, never silently True.
_row_no_fp = {"unavailable": {}, "chain": {"slug": "some-unit"}}
tmp, orig = with_telemetry([_row_no_fp])
_, _, trace_complete_absent = bench.schema_coverage()
restore(tmp, orig)
check("schema_coverage() reports trace_complete False when chain.fingerprint "
      "is absent, even though chain.slug is present",
      trace_complete_absent is False)

# Missing/unreadable telemetry file -> the honest (None, [], False) fallback.
tmp, orig = with_telemetry([])
tmp.unlink()  # the file itself does not exist at all
ratio_missing, missing_missing, trace_missing = bench.schema_coverage()
bench.TELEMETRY = orig
check("schema_coverage() falls back to (None, [], False) when telemetry.jsonl "
      "does not exist",
      (ratio_missing, missing_missing, trace_missing) == (None, [], False),
      str((ratio_missing, missing_missing, trace_missing)))

# --- local_repair_ratio() (objective 24) -------------------------------------

# One incident spanning multiple rows (same slug/attempts, rung changing as
# the incident progresses) must count as ONE outcome -- the last rung seen --
# not one per row. This is the specific regression case for the turn-vs-
# incident bug independent review found in the plan's original design.
_incident_rows = [
    {"chain": {"slug": "unit-a"}, "retries": {"attempts": 1, "rung": "repair"}},
    {"chain": {"slug": "unit-a"}, "retries": {"attempts": 1, "rung": "repair"}},
    {"chain": {"slug": "unit-a"}, "retries": {"attempts": 1, "rung": "restore"}},
]
tmp, orig = with_telemetry(_incident_rows)
ratio, counts = bench.local_repair_ratio()
restore(tmp, orig)
check("local_repair_ratio() counts one incident spanning multiple rows as "
      "ONE outcome (the last rung seen), not one per row",
      counts == {"restore": 1} and ratio == 1.0,
      f"got ratio={ratio!r} counts={counts!r}")

# Several distinct (slug, attempts) incidents, plus None-rung rows (skipped)
# and rows with no retries key at all (must not raise).
_mixed_rows: list[dict] = [
    {"chain": {"slug": "unit-a"}, "retries": {"attempts": 1, "rung": "repair"}},
    {"chain": {"slug": "unit-a"}, "retries": {"attempts": 2, "rung": "restore"}},
    {"chain": {"slug": "unit-b"}, "retries": {"attempts": 1, "rung": "block"}},
    {"chain": {"slug": "unit-c"}, "retries": {"attempts": 1, "rung": None}},
    {"chain": {"slug": "unit-d"}},
]
tmp, orig = with_telemetry(_mixed_rows)
ratio_mixed, counts_mixed = bench.local_repair_ratio()
restore(tmp, orig)
check("local_repair_ratio() computes the exact expected ratio and counts "
      "across distinct incidents, skipping None-rung and retries-less rows",
      counts_mixed == {"repair": 1, "restore": 1, "block": 1}
      and abs(ratio_mixed - (2 / 3)) < 1e-9,
      f"got ratio={ratio_mixed!r} counts={counts_mixed!r}")

# Every incident's rung is `block` -- the seeded violation this metric must
# be capable of reporting, not silently treating as healthy.
_all_block_rows = [
    {"chain": {"slug": "unit-a"}, "retries": {"attempts": 1, "rung": "block"}},
    {"chain": {"slug": "unit-b"}, "retries": {"attempts": 1, "rung": "block"}},
]
tmp, orig = with_telemetry(_all_block_rows)
ratio_block, counts_block = bench.local_repair_ratio()
restore(tmp, orig)
check("local_repair_ratio() reports ratio == 0.0 when every incident is "
      "block, not silently treated as healthy",
      ratio_block == 0.0 and counts_block == {"block": 2},
      f"got ratio={ratio_block!r} counts={counts_block!r}")

# No telemetry at all -> the honest (None, {}) fallback.
tmp, orig = with_telemetry([])
tmp.unlink()
ratio_none, counts_none = bench.local_repair_ratio()
bench.TELEMETRY = orig
check("local_repair_ratio() falls back to (None, {}) when telemetry.jsonl "
      "does not exist",
      (ratio_none, counts_none) == (None, {}), str((ratio_none, counts_none)))

if failures:
    print(f"\n{len(failures)} failed: " + "; ".join(failures))
    raise SystemExit(1)
print("\nAll bench tests passed")

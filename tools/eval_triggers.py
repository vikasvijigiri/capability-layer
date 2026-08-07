#!/usr/bin/env python3
"""Measure whether a skill's description actually triggers it.

Descriptions here were written by reasoning. That makes them plausible, not
demonstrated -- and the documented failure mode is **under-triggering**, which is
invisible from reading: the skill simply never fires and the work happens without
it. The only way to know is to run realistic prompts and count.

Method from `anthropics/skills` (`skill-creator`, description-optimization
section): ~20 queries per skill, roughly half that should trigger and half
near-misses that should not, each run through `claude -p` with the skill
available, scored on whether the skill was invoked.

    python tools/eval_triggers.py --list                     # what would run, free
    python tools/eval_triggers.py --skill code-review --dry-run
    python tools/eval_triggers.py --skill code-review        # SPENDS MONEY
    python tools/eval_triggers.py --all --repeats 3          # spends a lot

**Every real run costs one `claude -p` invocation per query per repeat.** That is
unattended spend, which `.claude/workflow.md` forbids without a decision, so the
default is `--dry-run` and `--all` refuses without `--yes-i-accept-the-cost`.

Query quality is the whole game. `skill-creator` is explicit that the negative
cases must be genuine near-misses -- sharing vocabulary with the skill but
needing something else. "Write a fibonacci function" as a negative for a PDF
skill tests nothing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
QUERIES = ROOT / "docs" / "evals" / "trigger-queries.json"


def load_queries() -> dict:
    try:
        raw = json.loads(QUERIES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # `_`-prefixed keys are notes for the reader. Counting `_method` as a skill
    # made `--list` report 421 queries across 3 skills, which is the length of a
    # sentence -- the first thing this harness measured was itself, wrongly.
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def run_query(query: str, timeout: int = 180) -> set[str]:
    """Which skills Claude actually invoked for this prompt.

    `--output-format json` carries the tool calls, so this reads what happened
    rather than asking the model to self-report -- a model asked "would you use
    a skill?" answers a different question than the one being measured.
    """
    try:
        proc = subprocess.run(
            ["claude", "-p", query, "--output-format", "json"],
            cwd=str(ROOT), capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    used: set[str] = set()
    for line in proc.stdout.splitlines():
        for name in {d.name for d in SKILLS.iterdir() if d.is_dir()}:
            if f'"{name}"' in line or f"skills/{name}/" in line:
                used.add(name)
    return used


def evaluate(skill: str, cases: list[dict], repeats: int, dry: bool) -> dict:
    hits = misses = false_fires = correct_silence = 0
    for case in cases:
        for _ in range(repeats):
            if dry:
                fired = case["should_trigger"]      # assume perfection, cost zero
            else:
                fired = skill in run_query(case["query"])
            if case["should_trigger"]:
                hits += fired
                misses += not fired
            else:
                false_fires += fired
                correct_silence += not fired
    pos = hits + misses
    neg = false_fires + correct_silence
    return {
        "skill": skill,
        "trigger_rate": round(hits / pos, 3) if pos else None,
        "false_fire_rate": round(false_fires / neg, 3) if neg else None,
        "positives": pos, "negatives": neg, "dry_run": dry,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--repeats", type=int, default=1)
    # Dry run is the default and `--live` is the opt-in, not the reverse. The
    # first version had only `--dry-run`, which could be turned on and never off.
    ap.add_argument("--live", action="store_true",
                    help="actually invoke claude -- this costs money")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="default; assumes every answer correct, costs nothing")
    ap.add_argument("--yes-i-accept-the-cost", action="store_true",
                    dest="accept", help="required for a real --all run")
    args = ap.parse_args(argv)

    data = load_queries()
    if not data:
        print(f"no query set at {QUERIES.relative_to(ROOT).as_posix()} -- "
              f"write one before measuring anything")
        return 1

    if args.list:
        total = sum(len(v) for v in data.values())
        print(f"{len(data)} skill(s), {total} queries")
        for name, cases in sorted(data.items()):
            pos = sum(1 for c in cases if c["should_trigger"])
            print(f"  {name:<24} {len(cases):>3} queries  ({pos} positive, "
                  f"{len(cases) - pos} near-miss)")
        print(f"\na real run costs {total} claude invocations per repeat")
        return 0

    targets = sorted(data) if args.all else ([args.skill] if args.skill else [])
    if not targets:
        print("give --skill NAME, --all, or --list")
        return 1

    dry = not args.live
    if args.all and not dry and not args.accept:
        cost = sum(len(data[t]) for t in targets) * args.repeats
        print(f"REFUSED: a real --all run is {cost} claude invocations. "
              f"Unattended spend needs a decision -- pass "
              f"--yes-i-accept-the-cost if that decision is yes.")
        return 1

    results = [evaluate(t, data[t], args.repeats, dry) for t in targets if t in data]
    print(json.dumps(results, indent=2))
    if dry:
        print("\nDRY RUN -- no claude invocations, every answer assumed correct. "
              "These numbers measure nothing; they prove the harness runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
import os
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


def validate(data: dict) -> list[str]:
    """Problems with the query set itself, checked before any money is spent.

    Three invariants, and the second is the one that is easy to get backwards.

    **Coverage.** A skill with no query set cannot be measured, so "it triggers"
    is an assertion about it rather than a finding. Coverage was 6 of 14 until
    2026-08-07 while every description was being tuned for triggering -- eight of
    them tuned blind.

    **One positive owner per query.** A query filed as a positive for its true
    owner and a NEGATIVE for a competitor is the strongest test in the set: it
    measures the competition that suppresses triggering, which is the failure mode
    that gets worse as each description individually improves. That is required,
    not forbidden. What is contradictory is one query expected to fire *two*
    skills -- whichever wins, at least one measurement is wrong by construction.

    **Shape.** A case missing `should_trigger` would be scored as a negative by
    `.get`, silently turning a positive into a false-fire test.
    """
    problems: list[str] = []
    known = {d.name for d in SKILLS.iterdir() if d.is_dir()} if SKILLS.is_dir() else set()

    for name, cases in data.items():
        if known and name not in known:
            problems.append(f"{name}: no such skill directory")
        if not isinstance(cases, list) or not cases:
            problems.append(f"{name}: query set is empty")
            continue
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or "query" not in case:
                problems.append(f"{name}[{index}]: no `query`")
            elif not isinstance(case.get("should_trigger"), bool):
                problems.append(
                    f"{name}[{index}]: `should_trigger` missing or not a bool -- "
                    f"it would be scored as a negative")

    for name in sorted(known - set(data)):
        problems.append(
            f"{name}: no query set, so its trigger rate cannot be measured at all")

    owners: dict[str, list[str]] = {}
    for name, cases in data.items():
        if not isinstance(cases, list):
            continue
        for case in cases:
            if isinstance(case, dict) and case.get("should_trigger") is True:
                owners.setdefault(str(case.get("query", "")).strip().lower(),
                                  []).append(name)
    for query, claimants in sorted(owners.items()):
        if len(claimants) > 1:
            problems.append(
                f"{query[:50]!r} is a positive for {claimants} -- a query may "
                f"have one expected owner; name it a negative for the others")
    return problems


def discrimination_pairs(data: dict) -> int:
    """Queries that are a positive for one skill and a named negative for another.

    The count worth watching. A set with none of these measures each description
    in isolation and cannot see the competition between them.
    """
    positives: dict[str, set[str]] = {}
    negatives: dict[str, set[str]] = {}
    for name, cases in data.items():
        if not isinstance(cases, list):
            continue
        for case in cases:
            if not isinstance(case, dict):
                continue
            bucket = positives if case.get("should_trigger") else negatives
            bucket.setdefault(str(case.get("query", "")).strip().lower(),
                              set()).add(name)
    return sum(1 for q in positives if negatives.get(q))


def run_query(query: str, timeout: int = 180) -> tuple[set[str], float]:
    """(skills actually invoked, cost in USD) for one prompt.

    **`--output-format json` does not work for this and the first version of this
    file used it.** That format returns only a result summary -- `result`,
    `usage`, `total_cost_usd`, `session_id` -- with no record of any tool call. So
    grepping it for a skill name could only ever match if the final prose happened
    to mention the skill, and the measured trigger rate came out at a uniform 0.1
    across two unrelated skills with a suspiciously perfect 0.0 false-fire rate.
    That was the instrument, not the descriptions. It cost about $29 to learn.

    `stream-json --verbose` emits every message, and an invocation appears as a
    `tool_use` block. Verified against a trivial prompt: `tool_use names: ['Read']`.

    Cost is returned rather than discarded, because a harness that spends real
    money silently is how you find out afterwards.
    """
    # Each invocation is a REAL session in this repository, so its post-run hook
    # would auto-commit whatever happens to be in the working tree -- forty times,
    # while an eval is running. `UAIOS_AUTOCOMMIT_RUNNING` is the re-entry guard
    # that hook already checks; setting it here is the same mechanism the check
    # runner uses when it spawns suites that would otherwise recurse.
    env = dict(os.environ, UAIOS_AUTOCOMMIT_RUNNING="1")
    try:
        proc = subprocess.run(
            ["claude", "-p", query, "--output-format", "stream-json", "--verbose"],
            cwd=str(ROOT), capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=timeout, env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return set(), 0.0

    known = {d.name for d in SKILLS.iterdir() if d.is_dir()}
    used: set[str] = set()
    cost = 0.0
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            cost += float(event.get("total_cost_usd") or 0.0)
        message = event.get("message") or {}
        blocks = message.get("content")
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            # A skill reaches the transcript as a `Skill` tool_use whose input
            # names it. Both spellings are accepted because the field name is the
            # harness's, not this repo's, and a rename would silently zero every
            # measurement -- the failure mode this function already had once.
            args = block.get("input") or {}
            for key in ("skill", "name", "skill_name"):
                value = args.get(key)
                if isinstance(value, str) and value in known:
                    used.add(value)
    return used, cost


def evaluate(skill: str, cases: list[dict], repeats: int, dry: bool,
             limit: int | None = None) -> dict:
    hits = misses = false_fires = correct_silence = 0
    spent = 0.0
    # Sample evenly across positives and negatives, so `--limit 4` is two of each
    # rather than four positives.
    if limit:
        pos_cases = [c for c in cases if c["should_trigger"]][: max(limit // 2, 1)]
        neg_cases = [c for c in cases if not c["should_trigger"]][: max(limit // 2, 1)]
        cases = pos_cases + neg_cases
    for case in cases:
        for _ in range(repeats):
            if dry:
                fired = case["should_trigger"]      # assume perfection, cost zero
            else:
                invoked, cost = run_query(case["query"])
                fired = skill in invoked
                spent += cost
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
        "cost_usd": round(spent, 4),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--repeats", type=int, default=1)
    # A live query measured at ~$0.72 on 2026-08-07, so a full 40-query run is
    # ~$29. Sampling exists so a harness change can be validated for ~$3 before
    # anyone commits to the full sweep.
    ap.add_argument("--limit", type=int,
                    help="use only N queries per skill, split evenly pos/neg")
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

    # Validated on every invocation, including --list, because --list is what the
    # test tier runs. A malformed set is cheaper to catch here than after 168
    # paid invocations have scored against it.
    problems = validate(data)

    if args.list:
        total = sum(len(v) for v in data.values())
        print(f"{len(data)} skill(s), {total} queries")
        for name, cases in sorted(data.items()):
            pos = sum(1 for c in cases if c.get("should_trigger"))
            print(f"  {name:<24} {len(cases):>3} queries  ({pos} positive, "
                  f"{len(cases) - pos} near-miss)")
        print(f"\ncross-skill discrimination pairs: {discrimination_pairs(data)}")
        print(f"a real run costs {total} claude invocations per repeat")
        if problems:
            print(f"\n{len(problems)} problem(s) with the query set:")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        return 0

    if problems:
        print(f"REFUSED: {len(problems)} problem(s) with the query set. Fix these "
              f"before spending anything on it:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    targets = sorted(data) if args.all else ([args.skill] if args.skill else [])
    if not targets:
        print("give --skill NAME, --all, or --list")
        return 1

    dry = not args.live
    if args.all and not dry and not args.accept:
        n = sum(min(len(data[t]), args.limit or len(data[t])) for t in targets)
        cost = n * args.repeats
        print(f"REFUSED: a real --all run is {cost} claude invocations "
              f"(~${cost * 0.72:.0f} at the measured per-query rate). "
              f"Unattended spend needs a decision -- pass "
              f"--yes-i-accept-the-cost if that decision is yes.")
        return 1

    results = [evaluate(t, data[t], args.repeats, dry, args.limit)
               for t in targets if t in data]
    print(json.dumps(results, indent=2))
    if not dry:
        _total = sum(r["cost_usd"] for r in results)
        print(f"\ntotal spend: ${_total:.2f}")
    if dry:
        print("\nDRY RUN -- no claude invocations, every answer assumed correct. "
              "These numbers measure nothing; they prove the harness runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

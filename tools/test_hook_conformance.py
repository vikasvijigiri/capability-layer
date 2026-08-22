#!/usr/bin/env python3
"""Objective 12 (production-grade by default) -- hook-contract conformance rate.

Reports a per-hook boolean vector against 5 statically-checkable clauses,
naming the failing clause(s) rather than a single pass/fail. Report only:
exits 0 unconditionally this pass, per `docs/specs/2026-08-21-qualitative-
objective-metrics.md`'s "report before gate" constraint -- gating is a
follow-up unit, after a baseline exists.

Clauses (see `docs/research/2026-08-22-cluster-d-b-grounding-refresh.md` for
the `github/awesome-copilot` `hooks.instructions.md` citation behind 1, 2, 4):

  1. payload read through `_hooklib.load_payload()`
  2. no unbounded/detached-process escape (relies on the host's implicit
     bounded timeout otherwise, which `hooks.instructions.md` treats as
     conformant -- "timeoutSec optional, default 30 seconds")
  3. one responsibility -- touches 0 or 1 state file under
     `.claude/hooks/state/`; 2+ is named but non-blocking this pass (see the
     plan's "Resolved at approval" note -- no live hook was confirmed to
     violate this before implementation, so a stricter gate would be invented)
  4. a representative-payload case exists somewhere in `tools/test_*.py`
  5. the module docstring states one of this skill's own four behavior
     classifications verbatim (`.claude/skills/capability-layer-maintenance/
     SKILL.md`'s "Hook contract" section: detect drift / enforce safety /
     record state / never author strategic content)

Run: python tools/test_hook_conformance.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / ".claude" / "settings.json"
TOOLS_DIR = ROOT / "tools"

DETACHED_PATTERNS = ("daemon=True", "multiprocessing.Process", "nohup",
                     "start_new_session=True")
BEHAVIOR_PHRASES = ("detect drift", "enforce safety", "record state",
                     "never author")
STATE_FILE_RE = re.compile(r"state[/\\]([\w.-]+\.(?:json|jsonl))", re.IGNORECASE)


def discover_hooks() -> list[Path]:
    """Every registered command hook, from `settings.json`.

    Mirrors `test_hook_standards.py`'s own discovery loop rather than
    importing it -- this file's declared scope is additive-only (see
    `docs/plans/2026-08-22-cluster-d-layer-self-grading.md` Task 2's Files
    list), so the pattern is repeated here in ~6 lines instead of extracting
    a shared helper from a file this task does not otherwise touch.
    """
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


def clause_1(source: str) -> bool:
    return "load_payload(" in source


def clause_2(source: str) -> bool:
    return not any(p in source for p in DETACHED_PATTERNS)


def clause_3(source: str) -> tuple[bool, int]:
    names = set(STATE_FILE_RE.findall(source))
    return (len(names) <= 1), len(names)


def clause_4(stem: str, all_test_source: str) -> bool:
    return stem in all_test_source


def clause_5(source: str) -> bool:
    docstring_match = re.match(r'^\s*"""(.*?)"""', source, re.DOTALL)
    docstring = docstring_match.group(1).lower() if docstring_match else ""
    return any(phrase in docstring for phrase in BEHAVIOR_PHRASES)


def main() -> int:
    hooks = discover_hooks()
    test_files = sorted(TOOLS_DIR.glob("test_*.py"))
    all_test_source = "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in test_files
    )

    fully_conforming = 0
    hard_conforming = 0
    c1_n = c2_n = c3_n = c4_n = c5_n = 0
    findings: list[str] = []
    for path in hooks:
        source = path.read_text(encoding="utf-8", errors="replace")
        stem = path.stem
        rel = path.relative_to(ROOT).as_posix()

        c1 = clause_1(source)
        c2 = clause_2(source)
        c3_ok, c3_count = clause_3(source)
        c4 = clause_4(stem, all_test_source)
        c5 = clause_5(source)
        c1_n += c1
        c2_n += c2
        c3_n += c3_ok
        c4_n += c4
        c5_n += c5

        failing = []
        if not c1:
            failing.append("clause 1 (no load_payload())")
        if not c2:
            failing.append("clause 2 (detached-process pattern found)")
        if not c3_ok:
            failing.append(f"clause 3 ({c3_count} state files touched, non-blocking)")
        if not c4:
            failing.append("clause 4 (no representative-payload test found)")
        if not c5:
            failing.append("clause 5 (no behavior classification in docstring)")

        hard_fail = not (c1 and c2 and c4)  # clauses 3 and 5 are named, never blocking
        if not hard_fail:
            hard_conforming += 1
        if not failing:
            fully_conforming += 1
        else:
            severity = "" if hard_fail else " (no hard-fail clause -- report only)"
            findings.append(f"{rel}: {', '.join(failing)}{severity}")

    total = len(hooks)
    print(f"objective 12 (hook-contract conformance) -- {total} live-wired hooks")
    print(f"  hard-conforming (clauses 1/2/4, blocking): {hard_conforming}/{total}")
    print(f"  fully conforming (all 5 clauses):          {fully_conforming}/{total}")
    print(f"  per-clause: 1 load_payload={c1_n}/{total}  2 bounded={c2_n}/{total}  "
          f"3 one-state-file={c3_n}/{total}  4 has-test={c4_n}/{total}  "
          f"5 declares-behavior={c5_n}/{total}")
    for f in findings:
        print(f"  {f}")
    print("\nReport only -- exits 0 regardless, per 'report before gate'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

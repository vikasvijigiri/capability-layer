#!/usr/bin/env python3
"""Architectural checks over `.claude/` — the mechanically decidable subset.

Why this is a subset, stated up front
-------------------------------------
The no-slop checklist this implements has fifteen categories. Most of them are
not decidable by a program: "is every sentence earning its place", "could Claude
misinterpret this", "is the intent immediately obvious" all need a reader.

A script that claimed to check those would be the fourth false-confidence gate
in this repo's history -- `03-review-gate`, `05-docs-gate` and `05-docs-required`
were all deleted for asserting a judgement they could not make. So this file
checks only what is falsifiable, and `.claude/skills/no-slop/SKILL.md` carries the
half that needs a human.

What is checked here, and which category it comes from:

  4  Prompt quality      hedging language in a document that gives instructions
  5  Token efficiency    description budget; file length as a god-skill smell
  1  Responsibility      every skill states its Success and Routing contract
  3  Trigger quality     every skill description says when NOT to use it
  6  Consistency         the same guidance sentence duplicated across files
  8  Safety              no credential pattern anywhere under .claude/

Run: python tools/test_no_slop.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
SKILLS = CLAUDE / "skills"
AGENTS = CLAUDE / "agents"

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


# --- 4. Prompt quality: hedging ----------------------------------------------
#
# A skill is an instruction, and an instruction that hedges transfers the
# decision back to the reader while looking like guidance. "Try to keep it
# short" is not a rule.
#
# Deliberately narrow. "may" and "can" are legitimate (permission, capability);
# only phrases that weaken an instruction are listed, and each must appear as a
# whole phrase rather than a substring.
HEDGES = [
    r"\btry to\b", r"\bmaybe\b", r"\bprobably should\b", r"\bif possible\b",
    r"\bgenerally speaking\b", r"\bit might be a good idea\b",
    r"\bwhere appropriate\b", r"\bas needed\b",
]
HEDGE_RE = re.compile("|".join(HEDGES), re.IGNORECASE)

for path in sorted(CLAUDE.rglob("*.md")):
    if "state" in path.parts:
        continue
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith((">", "#", "|")):
            continue  # quotes, headings and tables are not instructions
        m = HEDGE_RE.search(line)
        if m:
            rel = path.relative_to(ROOT).as_posix()
            fail(f"{rel}:{lineno} hedges: {m.group(0)!r} — say the rule or drop it")


# --- 5. Token efficiency, and 1/3: the per-skill contract --------------------
#
# Every skill is loaded in full when it fires and its description is injected
# every turn, so both have budgets. The structural sections are not style: a
# skill with no stated Success has no definition of done, and one with no
# Routing hard-codes nothing and hands off to nothing.
DESC_BUDGET = 500
SKILL_LINE_BUDGET = 200

for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
    md = d / "SKILL.md"
    if not md.is_file():
        fail(f".claude/skills/{d.name}/ has no SKILL.md — it is invisible")
        continue
    text = md.read_text(encoding="utf-8")
    rel = md.relative_to(ROOT).as_posix()

    # Prose lines only. A skill carrying an 80-line task template is not a
    # god-skill -- the template is a thing to copy, not an argument to follow.
    # Counting raw lines flagged `writing-plans` and `executing-plans`, which
    # are the two skills that legitimately ship templates, and would have made
    # the check permanently red. A permanently red check gets ignored, and this
    # repo has deleted three gates for exactly that.
    prose = re.sub(r"(?s)```.*?```", "", text)
    lines = len([ln for ln in prose.splitlines() if ln.strip()])
    if lines > SKILL_LINE_BUDGET:
        fail(f"{rel} is {lines} prose lines (budget {SKILL_LINE_BUDGET}) — "
             f"a god-skill smell; move detail to references/")

    desc = re.search(r"(?m)^description:\s*(.+)$", text)
    if not desc:
        fail(f"{rel} has no description — it can never be triggered")
    else:
        if len(desc.group(1)) > DESC_BUDGET:
            fail(f"{rel} description is {len(desc.group(1))} chars "
                 f"(budget {DESC_BUDGET}) — injected every turn")
        if "do not use" not in desc.group(1).lower():
            fail(f"{rel} description has no negative trigger — "
                 f"say when NOT to use it, or it overlaps its neighbours")

    for section in ("## Routing", "## Success"):
        if section not in text:
            fail(f"{rel} has no `{section}` section — "
                 f"{'no handoff contract' if 'Routing' in section else 'no definition of done'}")


# --- 6. Consistency: duplicated guidance -------------------------------------
#
# The "Duplicate Knowledge" smell. When the same sentence is maintained in three
# files, two of them go stale and nobody notices which. Only substantial
# sentences count -- short ones repeat legitimately.
MIN_DUP_CHARS = 90
sentences: dict[str, list[str]] = defaultdict(list)

for path in sorted(list(SKILLS.rglob("*.md")) + list(AGENTS.rglob("*.md"))):
    rel = path.relative_to(ROOT).as_posix()
    body = path.read_text(encoding="utf-8")
    body = re.sub(r"(?s)^---.*?---", "", body, count=1)          # frontmatter
    body = re.sub(r"(?s)```.*?```", "", body)                    # code blocks
    for raw in re.split(r"(?<=[.!?])\s+|\n\n", body):
        s = " ".join(raw.split())
        if len(s) >= MIN_DUP_CHARS and not s.startswith(("|", "#", "-", "*")):
            sentences[s].append(rel)

for sentence, where in sentences.items():
    if len(set(where)) > 1:
        fail(f"duplicated across {', '.join(sorted(set(where)))}: "
             f"{sentence[:70]}… — one owner, others point at it")


# --- 8. Safety: no credentials anywhere under .claude/ -----------------------
sys.path.insert(0, str(CLAUDE / "hooks"))
try:
    from _hooklib import SECRET_PATTERNS  # noqa: E402
except ImportError:
    notes.append("could not import _hooklib — credential scan skipped")
    SECRET_PATTERNS = []

# Only what git actually tracks. The hook logs live under .claude/ and capture
# tool payloads verbatim -- but they are gitignored, so "committed and shared"
# is false for them, and flagging one was this check's own first false positive.
import subprocess  # noqa: E402

try:
    _tracked = {
        (ROOT / line).resolve()
        for line in subprocess.run(
            ["git", "ls-files", ".claude"], cwd=str(ROOT), capture_output=True,
            text=True, timeout=30).stdout.splitlines() if line.strip()
    }
except (OSError, subprocess.SubprocessError):
    _tracked = set()
    notes.append("git ls-files failed -- credential scan skipped")

for path in sorted(CLAUDE.rglob("*")):
    if not path.is_file() or path.resolve() not in _tracked:
        continue
    try:
        body = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    # This file names the patterns it scans for; scanning itself is a false hit.
    if path.name in ("_hooklib.py", "01-secret-scan.py"):
        continue
    for pattern in SECRET_PATTERNS:
        if pattern.search(body):
            fail(f"{path.relative_to(ROOT).as_posix()} matches a credential "
                 f"pattern — .claude/ is committed and shared")
            break


print(f"scanned {len(list(SKILLS.iterdir()))} skills, "
      f"{len(list(AGENTS.glob('*.md')))} agents under .claude/\n")
for n in notes:
    print(f"  note: {n}")

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print(f"\n{len(failures)} finding(s).")
    print("Judgement-level checks are in the no-slop skill — this "
          "file only covers what a program can decide.")
    sys.exit(1)

print("OK: no hedging, every skill states its contract, no duplicated guidance, "
      "no credentials")
print("All no-slop tests passed")

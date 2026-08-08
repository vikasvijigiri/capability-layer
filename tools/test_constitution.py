#!/usr/bin/env python3
"""The constitution's articles and the plan gate that enforces them agree.

A principles file nobody checks against is decoration. The one thing that makes
this different from decoration is that every article has a corresponding
checkbox in the plan template, and every checkbox names a real article -- so an
article cannot be quietly dropped, and a gate cannot be invented that no article
backs.

That is the whole contract, and it is two set comparisons.

Run: python tools/test_constitution.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


CONSTITUTION = ROOT / ".claude" / "constitution.md"
PLANS_SKILL = ROOT / ".claude" / "skills" / "writing-plans" / "SKILL.md"

check("the constitution exists", CONSTITUTION.is_file(), str(CONSTITUTION))
check("writing-plans exists", PLANS_SKILL.is_file(), str(PLANS_SKILL))
if failures:
    sys.exit(1)

text = CONSTITUTION.read_text(encoding="utf-8")
skill = PLANS_SKILL.read_text(encoding="utf-8")

# `## IV — Reversibility` -> ("IV", "Reversibility")
articles = {m.group(1): m.group(2).strip()
            for m in re.finditer(r"(?m)^##\s+([IVX]+)\s*[—-]\s*(.+)$", text)}
# `- [ ] IV Reversibility — ...`
gates = {m.group(1): m.group(2).strip()
         for m in re.finditer(r"(?m)^- \[ \]\s+([IVX]+)\s+([A-Za-z][^—-]*)", skill)}

check("the constitution has articles", len(articles) >= 5, str(sorted(articles)))
check("the plan template has gates", len(gates) >= 5, str(sorted(gates)))

check("every article has a gate",
      set(articles) <= set(gates),
      f"ungated: {sorted(set(articles) - set(gates))}")
check("every gate names a real article",
      set(gates) <= set(articles),
      f"invented: {sorted(set(gates) - set(articles))}")

for num in sorted(set(articles) & set(gates)):
    a, g = articles[num].lower(), gates[num].lower()
    check(f"article {num} and its gate describe the same thing",
          a.split()[0] in g or g.split()[0] in a, f"{articles[num]!r} vs {gates[num]!r}")

# An unticked box is legal; an unticked box with no reason is not. The template
# must therefore offer somewhere to write the reason, or the rule is unusable.
check("the template provides a place to justify an exception",
      "complexity tracking" in skill.lower())

# Every article states a rule, not a heading. One line is enough; zero is a
# section someone meant to fill in later.
for num, title in articles.items():
    body = text.split(f"## {num}", 1)[1]
    body = re.split(r"(?m)^## ", body, maxsplit=1)[0]
    prose = [ln for ln in body.splitlines()[1:] if ln.strip()]
    check(f"article {num} ({title}) states a rule",
          len(prose) >= 1 and len(" ".join(prose)) > 40,
          f"{len(prose)} non-empty line(s)")

check("the skill points at the constitution by path",
      ".claude/constitution.md" in skill)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All constitution tests passed ({len(articles)} articles, {len(gates)} gates)")

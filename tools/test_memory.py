#!/usr/bin/env python3
"""Memory can be queried, and it says so when it knows nothing.

Why this suite exists
---------------------
`MEMORY.md` was written by every unit of work and read by nothing. The checklist
line this closes is "**Read**, not just written" -- and the definition-of-done
behind it is "memory from a prior run demonstrably changes behaviour on a later,
similar run". That is only demonstrable if a recorded fact about a path can be
shown coming back when a plan touches that path, which is what the first block
below does.

The second risk is subtler and is what most of this file guards: a rot detector
that cries wolf gets muted, and then the genuinely stale entries stay in forever.
It took three calibrations to get the false-positive rate to zero against this
repository's real notes -- bare filenames, partial paths, placeholders, and
entries that assert a file's *absence* -- so every one of those is pinned here.

Run: python tools/test_memory.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


# --- parsing ------------------------------------------------------------------
SAMPLE = """# Project Memory

## Hooks

- `.claude/hooks/_hooklib.py` owns the shared refusal rules.
- Hooks never author strategic content.

## Skills

- Skills live at `.claude/skills/<name>/SKILL.md`.
"""
parsed = memory.parse(SAMPLE, "MEMORY.md")
check("one entry per bullet, not per section", len(parsed) == 3, str(len(parsed)))
check("each entry carries its section",
      {e["section"] for e in parsed} == {"Hooks", "Skills"},
      str({e["section"] for e in parsed}))
check("a bullet's named paths are extracted",
      ".claude/hooks/_hooklib.py" in parsed[0]["paths"], str(parsed[0]))
check("a bullet naming no path has none", parsed[1]["paths"] == [], str(parsed[1]))

# --- the property the checklist actually asks for ------------------------------
#
# A fact recorded about a file comes back when work touches that file. Without
# this, memory is a diary.
hits = memory.relevant(parsed, [".claude/hooks/_hooklib.py"])
check("a recorded fact about a file is returned when work touches it",
      len(hits) == 1 and "refusal rules" in hits[0]["text"], str(hits))
check("...and says why it matched", hits[0]["why"] == "names the file", str(hits[0]))

near = memory.relevant(parsed, [".claude/hooks/post-run/06-artifact-autocommit.py"])
check("a fact about a sibling file matches by directory",
      any(h["why"] == "names its directory" for h in near), str(near))

check("an unrelated path matches nothing",
      memory.relevant(parsed, ["src/unrelated.py"]) == [],
      "a matcher that always returns something teaches its reader to skim")

check("a topic term matches prose with no path",
      any("strategic" in h["text"] for h in
          memory.relevant(parsed, [], terms=["strategic"])))

# --- rot, and every false positive that had to be calibrated out ---------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    tmp = Path(d)
    (tmp / ".claude" / "hooks" / "session-start").mkdir(parents=True)
    (tmp / ".claude" / "hooks" / "session-start" / "02-bootstrap.py").write_text(
        "x\n", encoding="utf-8")
    (tmp / "tools").mkdir()
    (tmp / "tools" / "loop.py").write_text("x\n", encoding="utf-8")

    (tmp / "MEMORY.md").write_text(
        "# M\n\n## S\n\n"
        "- `tools/gone_forever.py` does a thing.\n"          # genuinely missing
        "- `session-start/02-bootstrap.py` scaffolds.\n"     # partial path, exists
        "- `loop.py` classifies failures.\n"                 # bare name, exists
        "- `refs/uaios/green/<slug>` marks a tree.\n"        # placeholder
        "- A note about `.py` files in general.\n"           # bare suffix
        "- There is no `routing/process-skills.md`. Do not recreate one.\n",
        encoding="utf-8")

    entries = memory.load(tmp)
    rotten = memory.stale(entries, tmp)
    names = {p for e in rotten for p in e["missing"]}

    check("a genuinely deleted path is reported",
          "tools/gone_forever.py" in names, str(names))
    check("a PARTIAL path that exists deeper is not reported",
          "session-start/02-bootstrap.py" not in names,
          "three real entries were flagged this way; the rule resolves by basename")
    check("a BARE filename that exists is not reported",
          "loop.py" not in names, str(names))
    check("a PLACEHOLDER is not reported",
          not any("<" in n for n in names), str(names))
    check("a bare SUFFIX token is not reported", ".py" not in names, str(names))
    check("an entry asserting a file's ABSENCE is not reported",
          "routing/process-skills.md" not in names,
          "flagging it inverts the note's meaning")
    check("exactly one entry is rotten here", len(rotten) == 1, str(rotten))

    # Historical sources are excluded, and that is the calibration that took
    # the count from 26 to 1.
    check("only MEMORY.md is checked for rot",
          memory.ROT_SOURCES == ("MEMORY.md",),
          "an ADR naming a deleted file is the ADR working")

    # --- count rot ------------------------------------------------------------
    (tmp / ".claude" / "skills" / "alpha").mkdir(parents=True)
    (tmp / ".claude" / "skills" / "beta").mkdir(parents=True)
    (tmp / ".claude" / "agents").mkdir(parents=True)
    (tmp / ".claude" / "agents" / "one.md").write_text("x", encoding="utf-8")
    (tmp / "MEMORY.md").write_text(
        "# M\n\n## S\n\n- The layer has 9 skills and 1 agent.\n", encoding="utf-8")
    counts = memory.count_rot(tmp)
    claimed = {(c["noun"], c["claimed"], c["actual"]) for c in counts}
    check("a wrong count is caught", ("skill", 9, 2) in claimed, str(claimed))
    check("a correct count is not", not any(c["noun"] == "agent" for c in counts),
          f"1 agent claimed and 1 present: {claimed}")

# --- against the real repository ----------------------------------------------
#
# The defect class this session kept hitting was a function proved on synthetic
# input while the real input was what broke it. So the live tree is asserted too.
real = memory.load(ROOT)
check("the real repository has durable knowledge to query",
      len(real) > 20, f"{len(real)} entries")
check("it is clean of path rot and count rot right now",
      not memory.stale(real, ROOT) and not memory.count_rot(ROOT),
      f"stale={memory.stale(real, ROOT)[:1]} counts={memory.count_rot(ROOT)[:1]}")

# The one that proves the wiring, not just the tool: planning consults it.
plans_skill = (ROOT / ".claude/skills/writing-plans/SKILL.md").read_text(encoding="utf-8")
check("`writing-plans` queries memory before freezing the file map",
      "tools/memory.py" in plans_skill,
      "written-but-never-read is the gap this closes")
check("...and is told to say so when nothing is known",
      "nothing" in plans_skill.lower() and "memory.py" in plans_skill,
      "silence is indistinguishable from not having looked")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All memory tests passed ({len(real)} entries in the live tree)")

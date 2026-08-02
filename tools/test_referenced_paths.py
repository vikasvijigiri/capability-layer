#!/usr/bin/env python3
"""Every hook or tool path named in prose must exist, or be marked as gone.

Why this suite exists
---------------------
Prose in `.claude/` is executable instruction: a skill that says "run
`python .claude/hooks/pre-commit/03-review-gate.py --record`" is a command the
model will run. Nothing type-checks it.

On 2026-08-02 deleting three hooks broke four skills and one slash command --
`code-review` and `delivering` both instructed running a script that no longer
existed, and `/git-state` called two `_hooklib` helpers that had been removed.
Every suite stayed green through all of it, because `test_process_router.py`
checks routing entries and frontmatter, not claims. All five were found by
`grep`, by hand, after the fact.

The rule
--------
A referenced path must either **exist**, or appear on a line that says it is
gone. A tombstone is cheap to write and is the thing a reader actually needs;
silence is what costs. So this suite does not forbid naming a dead hook -- it
forbids naming one as though it were alive.

Run: python tools/test_referenced_paths.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / ".claude" / "hooks"

# Prose that is checked. Anything a human or the model reads as instruction.
SOURCES = [
    *(ROOT / ".claude").rglob("*.md"),
    ROOT / "CLAUDE.md",
    ROOT / "tools" / "README.md",
]

# Two shapes appear in this repo's prose:
#   a full path      `.claude/hooks/pre-commit/01-secret-scan.py`, `tools/x.py`
#   a bare hook name `04-delivery-guard.py`, resolved against .claude/hooks/*/
FULL_PATH_RE = re.compile(r"`([\w./-]*(?:\.claude/hooks|tools)/[\w./-]+\.py)`")
BARE_HOOK_RE = re.compile(r"`(\d{2}-[\w-]+\.py)`")

# A line carrying any of these is claiming the thing is gone, which is exactly
# what we want people to write. Deliberately narrow: "removed", "deleted" and
# "until <date>" are assertions about the past, not weasel words.
TOMBSTONE = re.compile(
    r"(?i)\b(deleted|removed|until it was|was the original|no longer|"
    r"were all|are in `?[0-9a-f]{7}|slated for deletion|comes off the deletion)\b")

failures: list[str] = []


def hook_names() -> set[str]:
    return {p.name for p in HOOKS_DIR.glob("*/*.py")}


def known_hooks() -> set[str]:
    """Bare filenames of every hook currently on disk."""
    return hook_names()


def resolve_bare(name: str) -> bool:
    return name in known_hooks()


def check_file(path: Path, live_hooks: set[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    rel = path.relative_to(ROOT).as_posix()

    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        # A tombstone rarely lands on the same line as the reference -- prose
        # wraps. Look at the sentence around it: two lines either side.
        window = chr(10).join(lines[max(0, lineno - 3):lineno + 2])
        excused = bool(TOMBSTONE.search(window))

        for match in FULL_PATH_RE.finditer(line):
            # NOT lstrip("./") -- that eats the leading dot of `.claude/`.
            target = match.group(1)[2:] if match.group(1).startswith("./") else match.group(1)
            if (ROOT / target).exists() or excused:
                continue
            failures.append(f"{rel}:{lineno} names `{target}`, which does not exist")

        for match in BARE_HOOK_RE.finditer(line):
            name = match.group(1)
            if resolve_bare(name) or excused:
                continue
            failures.append(
                f"{rel}:{lineno} names `{name}`, which is not a hook on disk")


live = known_hooks()
seen = set()
for source in SOURCES:
    if not source.is_file() or source in seen:
        continue
    seen.add(source)
    check_file(source, live)

print(f"{len(seen)} prose files scanned against {len(live)} hooks on disk")
print()

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print()
    print(f"{len(failures)} dangling reference(s).")
    print("Either fix the path, or say on the same line that it was deleted.")
    sys.exit(1)

print("OK: every hook and tool path named in prose resolves, or is marked gone")
print("All referenced-path tests passed")

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

import importlib.util
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
    r"(?i)(\b(delet(?:ed|ing)|removed|removing|was the original|no longer|"
    r"were all|slated for deletion|comes off the deletion)\b|until it was|until \d{4}-\d{2}-\d{2}|are in `?[0-9a-f]{7})")

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


# --- claims, not just paths -------------------------------------------------
#
# The path check above misses a whole class: prose that names something real by
# a name that is not a path. On 2026-08-03 `diff-reviewer` still told a subagent
# that `code-review` "records the receipt" -- a mechanism deleted the day before.
# No path appeared in that sentence, so nothing caught it.
#
# Four kinds of claim ARE mechanically checkable, and each has already rotted at
# least once in this repo:
#
#   a slash command   `/git-state`            -> .claude/commands/git-state.md
#   an env var        ALLOW_WIDE_STAGE        -> named in some live .py
#   a module symbol   `_hooklib.SECRET_...`   -> the attribute exists
#   a count           "nine hooks"            -> there are nine hooks
#
# What stays unguarded is a claim about *behaviour* ("records the receipt").
# That needs a reader, not a regex, and pretending otherwise would be the third
# false-confidence gate this repo has had to delete.

COMMANDS_DIR = ROOT / ".claude" / "commands"
COMMAND_RE = re.compile(r"`(/[a-z][a-z0-9-]*)`")
ENVVAR_RE = re.compile(r"`?\b((?:ALLOW|UAIOS)_[A-Z][A-Z0-9_]*)\b`?")
SYMBOL_RE = re.compile(r"`(_hooklib|_projectchecks)\.([A-Za-z_][A-Za-z0-9_]*)`")

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
}
COUNT_RE = re.compile(
    r"\b(" + "|".join(WORD_NUMBERS) + r"|\d{1,3})\s+(hooks|skills|suites|agents|events)\b",
    re.IGNORECASE)

# Built-in Claude Code commands, not files in this repo.
BUILTIN_COMMANDS = {"/verify", "/save", "/wip", "/skills-doctor", "/git-state",
                    "/fast", "/config", "/help", "/clear", "/loop", "/simplify",
                    "/code-review", "/run", "/init", "/review", "/schedule"}


def live_counts() -> dict:
    hooks_dir = ROOT / ".claude" / "hooks"
    event_dirs = [d for d in hooks_dir.iterdir()
                  if d.is_dir() and d.name not in {"state", "__pycache__"}]
    return {
        "hooks": len(list(hooks_dir.glob("*/*.py"))),
        "skills": len(list((ROOT / ".claude" / "skills").glob("*/SKILL.md"))),
        "suites": len(list((ROOT / "tools").glob("test_*.py"))),
        "agents": len(list((ROOT / ".claude" / "agents").glob("*.md"))),
        "events": len(event_dirs),
    }


def strip_fences(lines):
    """Drop fenced code blocks -- example output lives there, not claims."""
    out, in_fence = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return out


def module_symbols(name: str) -> set:
    spec = importlib.util.spec_from_file_location(
        f"_sym_{name}", HOOKS_DIR / f"{name}.py")
    if spec is None or spec.loader is None:
        return set()
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:  # noqa: BLE001 -- absent module reports as no symbols
        return set()
    return set(dir(mod))


counts = live_counts()
symbol_cache: dict[str, set] = {}

for source in sorted(seen):
    rel = source.relative_to(ROOT).as_posix()
    lines = strip_fences(source.read_text(encoding="utf-8").splitlines())

    for lineno, line in enumerate(lines, 1):
        window = chr(10).join(lines[max(0, lineno - 3):lineno + 2])
        excused = bool(TOMBSTONE.search(window))

        for cmd in COMMAND_RE.findall(line):
            if cmd in BUILTIN_COMMANDS or excused:
                continue
            if not (COMMANDS_DIR / f"{cmd.lstrip('/')}.md").is_file():
                failures.append(f"{rel}:{lineno} names command `{cmd}`, which has no file")

        for var in ENVVAR_RE.findall(line):
            if excused:
                continue
            hits = [p for p in list((ROOT / ".claude/hooks").rglob("*.py"))
                    + list((ROOT / "tools").glob("*.py"))
                    if var in p.read_text(encoding="utf-8", errors="ignore")]
            if not hits:
                failures.append(
                    f"{rel}:{lineno} names env var {var}, which no live source reads")

        for mod_name, attr in SYMBOL_RE.findall(line):
            if excused:
                continue
            if mod_name not in symbol_cache:
                symbol_cache[mod_name] = module_symbols(mod_name)
            if symbol_cache[mod_name] and attr not in symbol_cache[mod_name]:
                failures.append(
                    f"{rel}:{lineno} names `{mod_name}.{attr}`, which does not exist")

        for raw, noun in COUNT_RE.findall(line):
            if excused:
                continue
            claimed = WORD_NUMBERS.get(raw.lower(), None)
            if claimed is None:
                if not raw.isdigit():
                    continue
                claimed = int(raw)
            actual = counts[noun.lower()]
            if claimed != actual:
                failures.append(
                    f"{rel}:{lineno} claims {raw} {noun}, but there are {actual}")

print(f"{len(seen)} prose files scanned against {len(live)} hooks on disk")
print(f"live counts: {counts}")
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

#!/usr/bin/env python3
"""Every hook or tool path named in prose must exist, or be marked as gone.

Why this suite exists
---------------------
Prose in `.claude/` is executable instruction: a skill that says "run
`python .claude/hooks/permission-security/03-review-gate.py --record`" is a command the
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
#
# The root `README.md` was NOT here until 2026-08-08, and it is the one file most
# readers see first. It claimed "the thirteen skills" while there were fourteen,
# and drew the entry as a linear `task-brief → brainstormer → writing-plans` chain
# months after those became alternatives. Both were found by reading, not by this
# suite -- and when the count was deliberately broken to 13 as a test, the suite
# still exited 0, because the file was never scanned.
#
# `AGENTS.md` joins it for the same reason: it is the contract every non-Claude
# host reads, so a stale claim there is wrong for every harness at once.
SOURCES = [
    # `.claude/worktrees/` is gitignored -- a parallel-dispatch agent's own
    # isolated checkout, not this repo's prose. Its LOG.md/README.md/etc. are
    # a stale snapshot from whenever the worktree was created and will always
    # disagree with live counts; scanning them was drift-detection noise, not
    # a real finding. Confirmed live: it produced 554 false failures while
    # two such worktrees were mid-build (2026-08-22).
    *(p for p in (ROOT / ".claude").rglob("*.md")
      if "worktrees" not in p.relative_to(ROOT / ".claude").parts),
    ROOT / "CLAUDE.md",
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "tools" / "README.md",
]

# Two shapes appear in this repo's prose:
#   a full path      `.claude/hooks/permission-security/01-secret-scan.py`, `tools/x.py`
#   a bare hook name `04-delivery-guard.py`, resolved against .claude/hooks/*/
#
# The path is NOT anchored to the backticks, and requiring that was a real blind
# spot: the old pattern was `` `<path>` `` with the path filling the span, so it
# only matched a path quoted alone. Every actual reference is inside a command --
# `python tools/smoke.py --url ...` -- where the spaces break the closing anchor.
#
# Consequence, measured: `tools/smoke.py` is named by `releasing/SKILL.md` and
# `releasing/references/PLATFORMS.md`, and `tools/test_hooks.py` by
# `task-brief/SKILL.md`. Neither was copied by `install.py`, so every installed
# repo carried a mandated command that could not run -- and this suite passed in
# the target, scanning 30 prose files, for four days.
#
# Now matched anywhere, including inside fenced code blocks, which is where a
# runnable command usually lives. The `is marked gone` escape below still applies.
FULL_PATH_RE = re.compile(
    r"(?<![\w./-])((?:[\w.-]+/)*(?:\.claude/hooks|tools)/[\w./-]+\.py)\b")
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
# Known false-positive class: this matches any "<n> skills", including a
# descriptive quantity ("two different skills would both claim it") rather than
# an inventory claim ("the twelve skills above"). Left deliberately wide -- the
# run that first hit the false positive also caught two genuinely stale counts,
# so narrowing it costs more than rewording the odd sentence.
# Two holes this missed until 2026-08-04, both found by a count going stale with
# the suite green:
#
#   "four subagents"      -- `\bagents\b` has no word boundary inside "subagents",
#                            so the repo's most common phrasing was never checked.
#   "four fan-out agents" -- the number has to sit next to the noun, and one
#                            adjective between them was enough to slip through.
#
# The optional modifier must be HYPHENATED. That admits "fan-out agents" while
# still rejecting "four of the five agents", where the number is not the claim.
COUNT_RE = re.compile(
    r"\b(" + "|".join(WORD_NUMBERS) + r"|\d{1,3})\s+"
    r"(?:[a-z]+-[a-z]+\s+)?"
    r"(hooks|skills|capabilit(?:y|ies)|suites|sub-?agents|agents|events)\b",
    re.IGNORECASE)

# "capability"/"capabilities" is the word `.claude/README.md` uses for what
# every other file calls "skills" -- same inventory
# (`.claude/skills/*/SKILL.md`), different noun. Found live: it drifted to
# "14 capabilities" while every "skills"-worded count elsewhere had already
# moved to 15, undetected because the two words never met the same lookup.
NOUN_ALIASES = {"capability": "skills", "capabilities": "skills"}

# Built-in Claude Code commands, not files in this repo.
BUILTIN_COMMANDS = {"/verify", "/save", "/wip", "/git-state",
                    "/fast", "/config", "/help", "/clear", "/loop", "/simplify",
                    "/code-review", "/run", "/init", "/review", "/schedule",
                    # Claude Code's own bundled dynamic workflow -- ships with
                    # the harness, not something this repo defines a file for.
                    "/deep-research"}


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
            # "subagents" and "sub-agents" are the same inventory as "agents".
            noun_key = re.sub(r"^sub-?", "", noun.lower())
            noun_key = NOUN_ALIASES.get(noun_key, noun_key)
            actual = counts[noun_key]
            if claimed != actual:
                failures.append(
                    f"{rel}:{lineno} claims {raw} {noun}, but there are {actual}")

print(f"{len(seen)} prose files scanned against {len(live)} hooks on disk")
print(f"live counts: {counts}")
# --- CLAUDE.md obeys its own stated line limit, IF it states one --------------
#
# The limit is parsed FROM the file, so the file stays its own source of truth
# and this check cannot drift from it.
#
# This repo stated 320 until 2026-08-07 and no longer states anything, so the
# branch below is a deliberate skip rather than an oversight. The number was
# removed because it had started to distort edits: every genuine addition became
# a hunt for unrelated lines to delete, which is editing by budget instead of by
# judgement. The check stays because it costs nothing and a repo that does want a
# ceiling gets one by writing "max N lines" -- opt in, never imposed.
_claude_md = ROOT / "CLAUDE.md"
if _claude_md.is_file():
    _text = _claude_md.read_text(encoding="utf-8")
    _stated = re.search("(?i)max +([0-9]{2,4}) +lines", _text)
    if _stated:
        _limit = int(_stated.group(1))
        _actual = len(_text.splitlines())
        if _actual > _limit:
            failures.append(
                f"CLAUDE.md:1 states a max of {_limit} lines but is {_actual}. "
                f"Cut something, or change the stated limit deliberately.")
        else:
            print(f"OK: CLAUDE.md is {_actual} lines, under its stated {_limit}")
    else:
        print("OK: CLAUDE.md states no line limit -- nothing to enforce")

print()

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    print()
    print(f"{len(failures)} dangling reference(s).")
    print("Either fix the path, or say on the same line that it was deleted.")
    sys.exit(1)

# --- the authoring trees, and the docstrings that cite them ------------------
#
# `FULL_PATH_RE` above matches `.claude/hooks/**.py` and `tools/**.py` -- PYTHON
# ONLY. So `guide/how_to_create_hooks.md` and `templates/Skills.md` were never
# checked by anything, in any repository, and neither tree shipped in the payload
# until 2026-08-08.
#
# The consequence showed up where every consequence here shows up: in a target.
# `test_hook_standards.py` opens "Check repository hooks against
# guide/how_to_create_hooks.md", `test_process_router.py` quotes
# `guide/how_to_create_subagents.md` as the source of its proactive-clause rule,
# and `capability-layer-maintenance` tells the model to compare a new hook against
# `templates/` and `guide/`. In an installed repo all of it resolved to nothing,
# and a person following the skill went looking for directories that were not
# there.
#
# `.py` files are scanned too, which the `.md`-only pass above cannot do: the
# first of those citations is a module docstring.
DOC_PATH_RE = re.compile(r"(?<![\w./-])((?:guide|templates)/[\w.-]+\.md)\b")

doc_sources = list(SOURCES) + [
    p for p in sorted((ROOT / "tools").glob("*.py"))
] + [
    p for p in sorted((ROOT / ".claude").rglob("*.py"))
    if "__pycache__" not in p.parts and "worktrees" not in p.parts
]

doc_failures: list[str] = []
for path in doc_sources:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    for number, line in enumerate(text.splitlines(), 1):
        if TOMBSTONE.search(line):
            continue
        for match in DOC_PATH_RE.finditer(line):
            rel = match.group(1)
            if not (ROOT / rel).is_file():
                doc_failures.append(
                    f"{path.relative_to(ROOT).as_posix()}:{number} -> {rel}")

# --- a reference is named by its PATH, never by its bare stem ----------------
#
# Four audit skills became `<skill>/references/*.md` on 2026-08-07 and the
# artifact review became one too. Every document that had invoked them by name
# kept doing so, and nothing noticed: `/plan-review` said "Invoke
# `artifact-review`" for four days, naming a skill that no longer existed. The
# session reads that as a skill invocation, finds nothing, and continues -- the
# failure is silent, which is the whole reason it survived.
#
# So the rule is mechanical rather than a matter of care: a reference file may be
# cited by path, and a bare backticked stem is a finding. There is no judgement
# in it and no list to maintain -- the stems come off the disk.
REFERENCE_STEMS = {p.stem for p in (ROOT / ".claude" / "skills").glob("*/references/*.md")}
SKILL_DIRS = {p.name for p in (ROOT / ".claude" / "skills").iterdir() if p.is_dir()}
COMMAND_STEMS = {p.stem for p in (ROOT / ".claude" / "commands").glob("*.md")}
# A stem that is ALSO a live skill or command name is genuinely ambiguous and is
# left alone: `security-review` is both a reference and a command, and failing on
# the command would be a false positive.
BARE_STEMS = REFERENCE_STEMS - SKILL_DIRS - COMMAND_STEMS

stem_failures: list[str] = []
for source in sorted(seen):
    rel = source.relative_to(ROOT).as_posix()
    for number, line in enumerate(
            strip_fences(source.read_text(encoding="utf-8", errors="replace")
                         .splitlines()), 1):
        if TOMBSTONE.search(line):
            continue
        for stem in BARE_STEMS:
            if f"`{stem}`" in line:
                stem_failures.append(
                    f"{rel}:{number} names `{stem}` as if it were a skill; it is "
                    f"a reference -- cite its path")

if stem_failures:
    for item in stem_failures[:20]:
        print(f"FAIL: {item}")
    print(f"{len(stem_failures)} reference(s) named by bare stem. A stem reads as "
          f"a skill invocation and resolves to nothing, silently.")
    sys.exit(1)

if doc_failures:
    for item in doc_failures[:20]:
        print(f"FAIL: {item} does not exist")
    print(f"{len(doc_failures)} dangling authoring-doc reference(s). These are "
          f"cited by shipped files, so they must be in the payload as well as on "
          f"disk here.")
    sys.exit(1)

print(f"OK: every hook and tool path named in prose resolves, or is marked gone; "
      f"every guide/ and templates/ path cited by {len(doc_sources)} shipped "
      f"files exists")
print("All referenced-path tests passed")

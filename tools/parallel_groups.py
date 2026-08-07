#!/usr/bin/env python3
"""Which plan tasks may run at the same time, proved rather than assumed.

    python tools/parallel_groups.py docs/plans/2026-08-07-thing.md
    python tools/parallel_groups.py <plan> --json
    python tools/parallel_groups.py <plan> --strict     # fail on any serialized task

Why this exists
---------------
`executing-plans` said **never two implementers in parallel**, and it was right
for the reason it gave: "plan tasks touch overlapping files far more often than
they appear to." But that is an argument for *checking* overlap, not for banning
concurrency -- and the rule as written meant a twelve-task plan of genuinely
independent work ran twelve times slower than it had to.

`task-implementer` already carries `isolation: worktree`, whose own comment says
the constraint could be relaxed "deliberately rather than by forgetting it", and
names what isolation does not solve: frozen interfaces. This file is that
deliberate relaxation. Concurrency is licensed by a computed property of the
plan, so the licence is re-derivable, reviewable, and impossible to grant by
vibes at 2am.

Three rules decide a group:

  1. **Declared file sets.** A task with no `Files:` line cannot be grouped. Not
     a warning -- an undeclared file set is exactly the case the old rule was
     protecting against, and guessing it from the prose would reintroduce the
     failure while looking like a check.
  2. **Dependencies serialize.** `Depends on:` builds levels; a task never runs
     before something it consumes.
  3. **Shared surfaces serialize alone.** Migrations, lockfiles, and release
     configuration get a group to themselves even with disjoint files, because
     the conflict is in the resource, not the path. `.claude/workflow.md` already
     said this; nothing enforced it.

Exit 0 only when every task is groupable. The plan is the artifact under test.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_hl = _load(".claude/hooks/_hooklib.py", "hooklib_parallel")

# Reused, not re-listed. The migration table lives in `_hooklib` because the
# auto-commit gates on it, and a second copy here would drift the moment either
# changed -- the same defect as the three disagreeing commit tokenisers.
MIGRATION_PATTERNS: list[str] = list(_hl.MIGRATION_PATH_PATTERNS)

# Shared resources beyond migrations. A lockfile is one file that every task
# resolving a dependency writes; release config decides what ships. Two agents
# editing either produce a merge conflict that no worktree isolates away.
SHARED_PATTERNS = [
    "package-lock.json", "**/package-lock.json", "yarn.lock", "**/yarn.lock",
    "pnpm-lock.yaml", "**/pnpm-lock.yaml", "Cargo.lock", "**/Cargo.lock",
    "poetry.lock", "**/poetry.lock", "uv.lock", "**/uv.lock",
    "Gemfile.lock", "**/Gemfile.lock", "composer.lock", "**/composer.lock",
    "go.sum", "**/go.sum", "requirements.txt", "**/requirements.txt",
    ".github/workflows/*", "release.yaml", "release.yml", "**/release.yaml",
    ".claude/settings.json", ".claude/project-checks.json",
    "Dockerfile", "**/Dockerfile", "docker-compose.yml", "**/docker-compose.yml",
]

TASK_HEADER = re.compile(r"(?m)^#{2,4}\s+Task\s+(\d+)\s*[:.—-]?\s*(.*)$")

# Both forms of the same field, because `writing-plans` already emits the block
# one and it carries more information than the inline one:
#
#     **Files:** `a.py`, `b.py`                     inline
#
#     **Files:**                                    block
#     - Create: `a.py` — what it is for
#     - Modify: `b.py:symbol` — what changes
#
# The first version of this parser only matched inline, so it read zero files
# from every plan this repository has ever written and reported them all as
# unschedulable. A checker that rejects the format it is supposed to check gets
# deleted rather than adopted.
#
# The `\**` AFTER the colon is load-bearing and was missing at first: `**Files:**`
# closes its bold markup after the colon, so the value captured was literally
# `**` and every task reported one file named `**`. It parsed, it validated, and
# it was wrong in the direction that matters -- two tasks both "writing" `**`
# look like a collision, and two writing `**` and `**` look identical, so the
# scheduler's answers were arbitrary rather than merely useless.
# `[ \t]*` after the colon, never `\s*`. `\s` matches a newline, so a greedy
# `\s*(.*)$` under re.M skipped the line break and captured the FIRST BULLET of a
# block as though it were an inline value -- reading one file from a task that
# declared two. That is the worst possible failure for this module: it does not
# error, it under-reports the file set, and an under-reported file set is exactly
# what makes two colliding tasks look disjoint.
FILES_KEY = re.compile(r"(?im)^[ \t]*[-*]?[ \t]*\**files?\**[ \t]*:[ \t]*\**[ \t]*(.*)$")
DEPENDS_KEY = re.compile(
    r"(?im)^[ \t]*[-*]?[ \t]*\**(?:depends[ _-]?on|dependenc(?:y|ies))\**"
    r"[ \t]*:[ \t]*\**[ \t]*(.*)$"
)
# A `**Key:**` line ends the block above it. So does a blank line followed by
# anything that is not a bullet.
NEXT_KEY = re.compile(r"^\s*\**[A-Z][A-Za-z ]{2,24}\**\s*:")
BACKTICKED = re.compile(r"`([^`]+)`")


def normalise(path: str) -> str:
    # Markdown emphasis is not part of a filename. Stripped rather than matched
    # around, because a plan may bold a path anywhere: `**a.py**`, `*a.py*`.
    out = path.strip().strip("*_`").strip().strip(",;.").strip().replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out


def field(block: str, key: re.Pattern[str]) -> str | None:
    """One field's value, inline or as the bullet block beneath it.

    None means the field is absent, which is different from present-and-empty --
    the first is an unschedulable plan, the second is a task that claims to write
    nothing. Collapsing them would report the wrong problem.
    """
    match = key.search(block)
    if not match:
        return None
    inline = match.group(1).strip()
    if inline:
        return inline

    lines = block[match.end():].splitlines()
    collected: list[str] = []
    for line in lines:
        if not line.strip():
            if collected:
                break
            continue
        if NEXT_KEY.match(line):
            break
        if not line.lstrip().startswith(("-", "*", "+")):
            break
        collected.append(line.strip().lstrip("-*+ ").strip())
    return "\n".join(collected)


def parse_files(raw: str) -> list[str]:
    """Backticked paths if any are present, else comma-separated bare ones.

    Backticks win because a plan that marks its paths up is unambiguous, and one
    that does not still parses -- refusing the plain form would make the check
    something authors work around instead of with.

    A `path:symbol` reference resolves to the path. `Modify: \\`x.py:handler\\``
    names one file, and treating the symbol as part of the name would make two
    tasks editing different functions in one file look disjoint -- the exact
    overlap this scheduler exists to catch.
    """
    ticked = [normalise(m) for m in BACKTICKED.findall(raw)]
    candidates = ticked if ticked else [
        normalise(part) for part in re.split(r"[,\n]", raw)
    ]
    out: list[str] = []
    for item in candidates:
        if not item or re.fullmatch(r"(?i)\s*(none|n/?a|tbd|-)\s*", item):
            continue
        # Strip a leading `Create:` / `Modify:` / `Test:` label from the bare form.
        item = re.sub(r"(?i)^(create|modify|delete|test|add|edit|move)\s*:\s*", "",
                      item).strip()
        # `path:symbol` and `path:12` are both the one file at `path`. A Windows
        # drive letter (`C:/x`) is not a symbol reference, hence the length guard.
        if ":" in item and not re.match(r"^[A-Za-z]:[\\/]", item):
            item = item.split(":", 1)[0].strip()
        item = normalise(item)
        if item and item not in out:
            out.append(item)
    return out


def parse_depends(raw: str) -> tuple[list[int], str | None]:
    """(task numbers, problem). A dependency this cannot resolve is a problem.

    Three cases, and conflating any two of them is how a sequential plan gets
    reported as fully parallel:

      "none"              -> independent, stated
      "Task 2, Task 4"    -> resolvable
      "the store's API"   -> a real dependency on something with no task number,
                             which this cannot schedule and must not silently
                             treat as independence.

    The third case is not hypothetical. `docs/plans/2026-08-03-physrun-run-substrate.md`
    expresses its ordering entirely through `**Interfaces:**` prose, and the first
    version of this module read that as seven fully independent tasks -- a
    seven-way fan-out over work where the executor consumes the store. Wrong in
    the one direction that corrupts a tree rather than merely wasting a round.
    """
    if re.fullmatch(r"(?is)\s*(?:none|n/?a|nothing|-)\s*\.?\s*", raw or ""):
        return [], None
    numbers = sorted({int(n) for n in re.findall(r"\d+", raw or "")})
    if numbers:
        return numbers, None
    if (raw or "").strip():
        return [], (f"states a dependency this cannot resolve to a task number: "
                    f"{' '.join(raw.split())[:80]!r}. Reference the task by number, "
                    f"or write `none`")
    return [], None


def parse_plan(text: str) -> tuple[list[dict], list[str]]:
    """Tasks in document order, plus one problem string per unusable task."""
    problems: list[str] = []
    headers = list(TASK_HEADER.finditer(text))
    tasks: list[dict] = []

    for index, match in enumerate(headers):
        start = match.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[start:end]
        number = int(match.group(1))
        title = match.group(2).strip().strip("[]") or f"task {number}"

        raw_files = field(block, FILES_KEY)
        if raw_files is None:
            problems.append(
                f"Task {number} ({title[:40]}) declares no `Files:` field, so it "
                f"cannot be grouped. Add one listing every path the task writes."
            )
            continue
        files = parse_files(raw_files)
        if not files:
            problems.append(
                f"Task {number} ({title[:40]}) has an empty `Files:` list. A task "
                f"that writes nothing is not a task; a task that writes something "
                f"must say what."
            )
            continue

        # Absent is NOT "none". A task that never states its dependencies is
        # unschedulable for the same reason a task that never states its files is:
        # the safe default would be "depends on everything", which is the serial
        # plan this module exists to avoid, and the convenient default is
        # "depends on nothing", which is a seven-way fan-out over sequential work.
        # Neither guess is the author's, so neither is taken.
        raw_depends = field(block, DEPENDS_KEY)
        if raw_depends is None:
            problems.append(
                f"Task {number} ({title[:40]}) declares no `Depends on:` (or "
                f"`Dependencies:`) field. Write `none` to state independence -- "
                f"an absent field cannot be read as one, because the convenient "
                f"reading is a concurrent dispatch over work that is ordered."
            )
            continue
        depends, dep_problem = parse_depends(raw_depends)
        if dep_problem:
            problems.append(f"Task {number} ({title[:40]}) {dep_problem}")
            continue

        tasks.append({
            "number": number,
            "title": title,
            "files": files,
            "depends_on": depends,
        })

    numbers = [t["number"] for t in tasks]
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        problems.append(
            f"duplicate task number(s) {duplicates} -- dependencies reference "
            f"tasks by number, so two tasks sharing one is ambiguous"
        )
    return tasks, problems


def shared_surface(files: list[str]) -> list[str]:
    """Those paths that are a shared resource rather than a private file."""
    hits = []
    for rel in files:
        norm = normalise(rel)
        if any(fnmatch.fnmatch(norm, p) for p in MIGRATION_PATTERNS + SHARED_PATTERNS):
            hits.append(norm)
    return hits


def levels(tasks: list[dict]) -> tuple[list[list[dict]], list[str]]:
    """Kahn levels over `depends_on`. A cycle is reported, never worked around."""
    by_number = {t["number"]: t for t in tasks}
    problems: list[str] = []
    remaining = dict(by_number)
    for task in tasks:
        unknown = [d for d in task["depends_on"] if d not in by_number]
        if unknown:
            problems.append(
                f"Task {task['number']} depends on {unknown}, which no task "
                f"in this plan defines"
            )
    resolved: set[int] = set()
    out: list[list[dict]] = []
    while remaining:
        ready = [
            t for t in remaining.values()
            if all(d in resolved or d not in by_number for d in t["depends_on"])
        ]
        if not ready:
            problems.append(
                f"dependency cycle among tasks {sorted(remaining)} -- no order "
                f"exists, so no schedule does either"
            )
            break
        ready.sort(key=lambda t: t["number"])
        out.append(ready)
        for task in ready:
            resolved.add(task["number"])
            remaining.pop(task["number"])
    return out, problems


def group_level(level: list[dict]) -> list[list[dict]]:
    """Split one dependency level into groups no two of whose tasks collide.

    First fit rather than optimal packing. An optimal partition would be a
    graph-colouring problem whose answer nobody can verify by reading it, and the
    cost of one extra group is one extra round -- much cheaper than a scheduler
    no reviewer trusts.
    """
    groups: list[list[dict]] = []
    for task in level:
        if shared_surface(task["files"]):
            groups.append([task])          # alone, by rule 3
            continue
        owned = set(task["files"])
        for group in groups:
            if len(group) == 1 and shared_surface(group[0]["files"]):
                continue
            if any(owned & set(other["files"]) for other in group):
                continue
            group.append(task)
            break
        else:
            groups.append([task])
    return groups


def schedule(text: str) -> dict:
    tasks, problems = parse_plan(text)
    if not tasks and not problems:
        problems.append(
            "no `### Task N:` headings found -- either this is not a plan, or its "
            "tasks are not numbered, and an unnumbered task cannot be depended on"
        )

    tiers, level_problems = levels(tasks)
    problems.extend(level_problems)

    groups: list[dict] = []
    for tier_index, tier in enumerate(tiers, 1):
        for group in group_level(tier):
            files = sorted({f for t in group for f in t["files"]})
            groups.append({
                "level": tier_index,
                "tasks": [t["number"] for t in group],
                "titles": [t["title"] for t in group],
                "files": files,
                "serialized": bool(shared_surface(files)),
                "reason": ("shared surface: " + ", ".join(shared_surface(files)))
                          if shared_surface(files) else "",
                "concurrency": len(group),
            })

    parallel = [g for g in groups if g["concurrency"] > 1]
    return {
        "tasks": len(tasks),
        "groups": groups,
        "rounds": len(groups),
        "max_concurrency": max((g["concurrency"] for g in groups), default=0),
        "parallel_groups": len(parallel),
        "serialized_groups": len([g for g in groups if g["serialized"]]),
        "problems": problems,
        "valid": not problems,
    }


def render(result: dict) -> str:
    out: list[str] = []
    out.append(f"tasks {result['tasks']}   rounds {result['rounds']}   "
               f"max concurrency {result['max_concurrency']}")
    out.append("")
    for index, group in enumerate(result["groups"], 1):
        tag = "SERIAL" if group["serialized"] else f"x{group['concurrency']}"
        names = ", ".join(f"{n}" for n in group["tasks"])
        out.append(f"  round {index:<3} {tag:<7} task(s) {names}")
        for number, title in zip(group["tasks"], group["titles"], strict=False):
            out.append(f"      {number}. {title[:70]}")
        if group["reason"]:
            out.append(f"      -> {group['reason']}")
    if result["problems"]:
        out.append("")
        out.append(f"{len(result['problems'])} problem(s) -- the plan is not schedulable:")
        for problem in result["problems"]:
            out.append(f"  - {problem}")
    else:
        out.append("")
        out.append(f"schedulable: {result['parallel_groups']} group(s) may run "
                   f"concurrently, {result['serialized_groups']} must not.")
        out.append("Dispatch one `task-implementer` per task within a round, all in "
                   "the SAME message. Verify the whole round before the next.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan", help="path to the plan document")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--strict", action="store_true",
                    help="also fail when any group had to be serialized")
    args = ap.parse_args(argv)

    path = Path(args.plan)
    if not path.is_file():
        print(f"no such plan: {path}", file=sys.stderr)
        return 2

    result = schedule(path.read_text(encoding="utf-8", errors="replace"))
    print(json.dumps(result, indent=2) if args.as_json else render(result))

    if not result["valid"]:
        return 1
    if args.strict and result["serialized_groups"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

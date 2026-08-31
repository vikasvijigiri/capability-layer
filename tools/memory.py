#!/usr/bin/env python3
"""What does this repository already know about the files I am about to touch?

    python tools/memory.py --plan docs/plans/2026-08-10-thing.md
    python tools/memory.py --paths tools/loop.py .claude/hooks/_hooklib.py
    python tools/memory.py --stale        # entries naming a path that is gone
    python tools/memory.py --json

The gap this closes
-------------------
`MEMORY.md` was written on every unit of work and **read by nothing**. Planning
never opened it, so a convention learned in one session could not change a plan
written in the next -- which makes the file a diary rather than memory. A
knowledge store nobody queries is worse than none, because writing to it feels
like the work is being retained.

This is the read side. `writing-plans` queries it at Stage C1 with the file map
it is about to freeze, so what the repository already knows arrives *before* the
plan commits to an approach rather than in review afterwards.

Relevance, and why it is deliberately blunt
-------------------------------------------
An entry is relevant to a path when it *names* that path, or names the directory
it sits in. That is a keyword match, not a semantic one, and it is the right
trade: the failure mode of a clever matcher is confident silence -- it returns
nothing and the caller concludes there is nothing to know. A blunt matcher
returns a few extra lines, which cost a reader seconds.

Rot is the same question, asked backwards
------------------------------------------
`--stale` lists entries naming a path that no longer exists. Memory rots exactly
where the repository moved and the note did not, and those entries are worse
than absent ones because they read as current. This is the compaction signal:
it says *what* to prune rather than pruning on a schedule, which is what keeps
a durable file from being trimmed by age instead of by truth.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The files that hold durable knowledge, as `knowledge-manager` defines them.
# `LOG.md` is deliberately absent: it is chronological history, and matching a
# plan against every past event returns the whole file.
SOURCES = ("MEMORY.md", "ISSUES.md")
DECISIONS = "decisions"

# Rot is only meaningful where a file asserts a CURRENT fact. `MEMORY.md` is the
# only one that does -- `knowledge-manager` defines it as "a convention that
# outlives the task", while `ISSUES.md` is one entry per past incident and
# `decisions/` records why something was removed. Checking those two reported
# twenty-six stale entries, nearly all of them healthy history.
ROT_SOURCES = ("MEMORY.md",)

# Counts stated in prose are the other way memory rots, and the commoner one:
# a path that moves is noticed, a number that drifts is not. `MEMORY.md` claimed
# 22 skills and 10 agents while the tree held 14 and 11.
COUNT_CLAIM = re.compile(r"(\d+)\s+(skills?|agents?|hooks?|suites?)\b", re.I)

# Notes that assert a file's ABSENCE. `MEMORY.md` says "There is no
# `routing/process-skills.md` keyword router. Do not recreate one" -- that path
# is missing on purpose, and reporting it as rot is backwards. The mention and
# the prohibition look identical to a substring match, which is the same reason
# `test_process_router.py` carries a negation test beside its verb scan.
NEGATED_WORDS = {"no", "not", "never", "removed", "deleted",
                 "gone", "absent", "stop", "avoid"}

# A backticked token that looks like a path. Same shape the minimal-diff gate
# uses, and for the same reason: prose here is full of backticked words that are
# symbols, not files.
PATH_TOKEN = re.compile(r"`([^`\n]+)`")


def _looks_like_path(token: str) -> bool:
    token = token.strip()
    if not token or " " in token or "\t" in token:
        return False
    return "/" in token or token.endswith((".md", ".py", ".json", ".yml", ".yaml"))


def parse(text: str, source: str) -> list[dict]:
    """`## Section` + `- bullet` -> entries carrying their own named paths.

    One entry per bullet rather than per section: a section here runs to a dozen
    unrelated facts, and returning all twelve because one matched is how a query
    tool trains its reader to skim past it.
    """
    entries: list[dict] = []
    section = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        stripped = line.strip()
        if not stripped.startswith(("- ", "* ")):
            continue
        body = stripped[2:].strip()
        if not body:
            continue
        paths = {t for t in PATH_TOKEN.findall(body) if _looks_like_path(t)}
        entries.append({
            "source": source,
            "section": section,
            "text": body,
            "paths": sorted(paths),
        })
    return entries


def load(root: Path | None = None) -> list[dict]:
    """Every entry from every durable source. A missing source contributes none."""
    root = Path(root or ROOT)
    entries: list[dict] = []
    for name in SOURCES:
        path = root / name
        if not path.is_file():
            continue
        try:
            entries.extend(parse(path.read_text(encoding="utf-8", errors="ignore"),
                                 name))
        except OSError:
            continue
    decisions = root / DECISIONS
    if decisions.is_dir():
        for adr in sorted(decisions.glob("*.md")):
            try:
                head = adr.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            title = next((ln[2:].strip() for ln in head.splitlines()
                          if ln.startswith("# ")), adr.stem)
            paths = {t for t in PATH_TOKEN.findall(head) if _looks_like_path(t)}
            entries.append({
                "source": f"{DECISIONS}/{adr.name}",
                "section": "decision",
                "text": title,
                "paths": sorted(paths),
            })
    return entries


def relevant(entries: list[dict], paths, terms=None) -> list[dict]:
    """Pure. Entries naming one of `paths`, its directory, or one of `terms`.

    Directory-level matching is intentional and is the opposite of the rule the
    minimal-diff gate uses. There, a directory match was too generous because it
    granted permission; here it only surfaces a note to read, and a convention
    recorded about `.claude/hooks/` is exactly what someone editing a hook needs.
    """
    wanted = {str(p).replace("\\", "/") for p in (paths or [])}
    dirs = {p.rsplit("/", 1)[0] for p in wanted if "/" in p}
    terms = {t.lower() for t in (terms or []) if t}

    hits = []
    for entry in entries:
        named = set(entry["paths"])
        if named & wanted:
            hits.append({**entry, "why": "names the file"})
            continue
        # Prefix in EITHER direction. A note about `.claude/hooks/_hooklib.py`
        # is exactly what someone editing `.claude/hooks/stop-finalization/06-*.py`
        # needs, and comparing directories for equality missed it -- one is
        # nested below the other. Nesting is the common shape in this layer, so
        # equality would have made directory matching almost never fire.
        entry_dirs = {n.rsplit("/", 1)[0] for n in named if "/" in n}
        if any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
               for a in entry_dirs for b in dirs):
            hits.append({**entry, "why": "names its directory"})
            continue
        if terms and any(t in entry["text"].lower() for t in terms):
            hits.append({**entry, "why": "mentions the topic"})
    return hits


def stale(entries: list[dict], root: Path | None = None) -> list[dict]:
    """Entries naming a path that no longer exists.

    The compaction signal. An entry that points at a deleted file is worse than
    a missing one: it reads as current, and the reader has no way to tell.
    """
    root = Path(root or ROOT)
    out = []
    for entry in entries:
        # `decisions/` is excluded, and that is the whole calibration. An ADR
        # naming a deleted file is the ADR doing its job -- half of them exist
        # to record that something WAS removed and why. Rot detection belongs on
        # files that assert a CURRENT fact, which is `MEMORY.md` and `ISSUES.md`.
        # Including ADRs reported twenty "rotten" entries, nearly all healthy.
        if entry["source"] not in ROT_SOURCES:
            continue
        # An entry asserting a file's ABSENCE is not rot. `MEMORY.md` carries
        # "There is no `routing/process-skills.md` keyword router. Do not
        # recreate one" -- that path is missing on purpose, and flagging it
        # inverts the note's meaning. A mention and a prohibition are identical
        # to a path scan, which is why the negation test is here rather than in
        # the matcher.
        # Tokenise the PROSE only -- the backticked spans are stripped first.
        # `tools/gone_forever.py` contains the word "gone", so tokenising the
        # whole line made a genuinely deleted file read as a deliberate absence.
        # The negation is a property of the sentence, never of the filename.
        prose = PATH_TOKEN.sub(" ", entry["text"]).lower()
        if NEGATED_WORDS & set(re.findall(r"[a-z]+", prose)):
            continue
        gone = [p for p in entry["paths"] if _definitely_missing(root, p)]
        if gone:
            out.append({**entry, "missing": gone})
    return out


def count_rot(root: Path | None = None) -> list[dict]:
    """Count claims in `MEMORY.md` that disagree with the tree.

    A number nobody enforces is a number that rots, and it rots silently: a
    reader has no way to tell 22 from 14 without counting. This counts.
    """
    root = Path(root or ROOT)
    actual = {
        "skill": len([d for d in (root / ".claude/skills").iterdir() if d.is_dir()])
        if (root / ".claude/skills").is_dir() else None,
        "agent": len(list((root / ".claude/agents").glob("*.md")))
        if (root / ".claude/agents").is_dir() else None,
    }
    path = root / "MEMORY.md"
    if not path.is_file():
        return []
    out = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    for line in text.splitlines():
        for num, noun in COUNT_CLAIM.findall(line):
            key = noun.rstrip("s").lower()
            if actual.get(key) is None:
                continue
            if int(num) != actual[key]:
                out.append({"source": "MEMORY.md", "text": line.strip()[:110],
                            "claimed": int(num), "actual": actual[key],
                            "noun": key})
    return out


def _definitely_missing(root: Path, token: str) -> bool:
    """Only a repo-relative path that resolves nowhere. Everything else is skipped.

    The first version checked `(root / token).exists()` for every token and
    reported `loop.py`, `resume.py` and `workflow.md` as deleted -- all three
    exist, just not at the repository root, because an ADR refers to a file by
    its bare name. Twenty-six "rotten" entries, most of them healthy.

    A rot detector that cries wolf is worse than none: it gets muted, and the
    genuinely stale entries stay in. So the rule is narrow on purpose -- a token
    is only missing when it names a directory path that resolves nowhere, and a
    bare filename is checked by basename anywhere in the tree instead.
    """
    if "*" in token or token.startswith(("..", "/", "~", "http")):
        return False
    if "<" in token or ">" in token:
        return False          # a placeholder like `refs/uaios/green/<slug>`
    if token.startswith(".") and "/" not in token and token.count(".") == 1:
        return False          # a bare suffix like `.py`, written as a token

    # Resolve by BASENAME anywhere in the tree, never by the literal token.
    #
    # Third calibration, and the last: notes refer to files by partial path --
    # `session-init/02-session-context.py` for something that lives under
    # `.claude/hooks/`. Checking `root / token` reported three such entries as
    # deleted while all three were present one directory up.
    #
    # The rule is deliberately conservative. A file that moved between
    # directories is NOT reported, and that is the trade taken on purpose: a rot
    # detector that cries wolf gets muted, and then the genuinely stale entries
    # stay in forever. Missing the odd move is recoverable; being ignored is not.
    name = token.rstrip("/").rsplit("/", 1)[-1]
    if not name:
        return False
    if (root / token).exists():
        return False

    # A deliberately IGNORED path is not rot, and this rule exists because CI
    # found what no local run could. `MEMORY.md` names
    # `.claude/settings.local.json`, which is gitignored: present on a developer
    # machine, absent from a fresh checkout. The detector passed locally and
    # failed in CI on the same commit -- the fourth calibration, and the first
    # that was environment-dependent rather than pattern-dependent.
    #
    # `git check-ignore` answers it definitively, and a git that cannot run
    # yields no opinion rather than a false positive.
    try:
        ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", token],
                                 capture_output=True, timeout=10)
        if ignored.returncode == 0:
            return False
    except (OSError, subprocess.SubprocessError):
        return False
    try:
        return not any(root.rglob(name))
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paths", nargs="*", default=None)
    ap.add_argument("--plan", default=None,
                    help="query with the paths a plan declares")
    ap.add_argument("--terms", nargs="*", default=None)
    ap.add_argument("--stale", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    entries = load(root)

    if args.stale:
        rotten = stale(entries, root)
        counts = count_rot(root)
        if args.json:
            print(json.dumps(rotten, indent=2))
        else:
            for entry in rotten:
                print(f"[{entry['source']}] {entry['text'][:90]}")
                print(f"    missing: {', '.join(entry['missing'])}")
            for c in counts:
                print(f"[{c['source']}] claims {c['claimed']} {c['noun']}(s), "
                      f"the tree has {c['actual']}")
                print(f"    {c['text']}")
            print(f"\n{len(rotten)} entry(ies) name a missing path and "
                  f"{len(counts)} count claim(s) disagree with the tree, "
                  f"out of {len(entries)} known")
        return 1 if (rotten or counts) else 0

    paths = args.paths
    if args.plan:
        # Reuse scope's plan parser rather than adding a third reader of the
        # plan format -- the tier, the minimal-diff gate and this must agree
        # about what a plan declares.
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            import scope
            paths = scope.plan_paths(Path(args.plan)) or []
        except Exception:
            paths = []

    hits = relevant(entries, paths, args.terms)
    if args.json:
        print(json.dumps(hits, indent=2))
    else:
        for entry in hits:
            print(f"[{entry['source']}] ({entry['why']}) {entry['text']}")
        # Saying "nothing known" out loud matters as much as the hits. Silence
        # reads as "the tool did not run".
        print(f"\n{len(hits)} relevant entry(ies) from {len(entries)} known, "
              f"over {len(paths or [])} path(s)"
              + ("" if hits else " -- nothing recorded about these files"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

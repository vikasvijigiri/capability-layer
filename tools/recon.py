#!/usr/bin/env python3
"""What is this repository, and what in it is unfinished. Facts only.

    python tools/recon.py                 # human-readable
    python tools/recon.py --json          # the same facts, for a skill to consume
    python tools/recon.py --units         # just the parallel recon units

Why this exists
---------------
The chain's entry frames a *request*. Nothing owned the
question a dropped-in layer actually faces first: *what is this repo and what is
half-built in it*. The audit on 2026-08-07 found the gap by running
`tools/resume.py` against this repository after 104 commits of finished work and
getting `state=PLANNING` -- because state keys off `docs/plans/<slug>.md`, and a
repo that has never used this layer has none. The engine was not wrong; it had
nothing to read.

So this reads what every repository does have: its tree, its manifests, its
tests, its branches, and the markers people leave where they stopped.

The design constraint that matters is **this script never judges**. It counts
and it locates. `repo-recon` decides what the findings mean, because that needs
a model and this needs to be reproducible. Every number here is re-derivable by
a second run.

`--units` is the part that earns its place: it partitions the tree into
subsystems with **disjoint file sets**, which is exactly the precondition
`parallel_groups.py` enforces for concurrent agents. One `researcher` per
unit, all dispatched in one message, no two reading the same file twice.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NOISE_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "dist", "build", "out", ".next", ".nuxt",
    "target", "vendor", "coverage", ".tox", ".gradle", "Pods", ".terraform",
    # This repository's own parallel-worktree convention
    # (decisions/2026-08-21-branch-per-parallel-task.md, `tools/worktree.py`'s
    # `WORKTREE_DIR`). A nested worktree is a full checkout of this same repo,
    # so scanning into it double-counts every test file and fixture string it
    # contains under a different path -- found when a left-behind worktree made
    # test_recon.py fail on its own "no skipped test outside this suite's own
    # fixtures" assertion, reporting the SAME fixture line twice, once at its
    # real path and once inside the worktree.
    ".worktrees",
}

# One row per ecosystem: manifest -> (language, install, test). The same data-table
# shape `_projectchecks.MARKER_CHECKS` uses, and for the same reason -- a new
# ecosystem should be a row, not a branch.
MANIFESTS: tuple[tuple[str, str, str, str], ...] = (
    ("package.json", "javascript/typescript", "npm install", "npm test"),
    ("pyproject.toml", "python", "pip install -e .", "pytest"),
    ("requirements.txt", "python", "pip install -r requirements.txt", "pytest"),
    ("setup.py", "python", "pip install -e .", "pytest"),
    ("Cargo.toml", "rust", "cargo build", "cargo test"),
    ("go.mod", "go", "go build ./...", "go test ./..."),
    ("pom.xml", "java", "mvn install", "mvn test"),
    ("build.gradle", "java/kotlin", "gradle build", "gradle test"),
    ("build.gradle.kts", "kotlin", "gradle build", "gradle test"),
    ("Gemfile", "ruby", "bundle install", "bundle exec rspec"),
    ("composer.json", "php", "composer install", "vendor/bin/phpunit"),
    ("mix.exs", "elixir", "mix deps.get", "mix test"),
    ("deno.json", "deno", "deno cache", "deno test"),
    ("Makefile", "make", "make", "make test"),
)

# Where someone stopped. Ordered by how strongly each implies unfinished work
# rather than a note: a raise NotImplementedError is a promise nobody kept.
UNFINISHED = (
    (re.compile(r"\braise\s+NotImplementedError"), "not-implemented"),
    (re.compile(r"\bTODO\b"), "todo"),
    (re.compile(r"\bFIXME\b"), "fixme"),
    (re.compile(r"\bXXX\b"), "xxx"),
    (re.compile(r"\bHACK\b"), "hack"),
    # Anchored on purpose. An unanchored `xit\(` matches `exit(`, which reported
    # 49 skipped tests in a repository that has none -- found by running this
    # against its own repo, which is the only reason it was ever visible.
    (re.compile(r"@(?:pytest\.mark\.)?skip\b|@unittest\.skip"
                r"|\bskip(?:If|Unless|Test)\(|\bit\.skip\(|\bdescribe\.skip\("
                r"|\bxit\(|\bxdescribe\(|\btest\.skip\(|\bt\.Skip\("), "skipped-test"),
    (re.compile(r"\bWIP\b"), "wip"),
)

# `test_*.py` is pytest's default discovery pattern and was missing from the
# first version of this, which then reported "0 test files over 47 code files"
# for a repository whose entire suite is `tools/test_*.py`. A test-topology
# reading that is silently zero is worse than none: it reads as "no tests here"
# and every downstream judgement inherits it.
TEST_HINTS = re.compile(
    r"(^|/)(tests?|spec|specs|__tests__|e2e|integration|features)(/|$)"
    r"|(^|/)(test_|spec_|conftest)"
    r"|(_test|_spec|Test|Tests|Spec|\.test|\.spec)\.",
)

CODE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".rs", ".go", ".java",
    ".kt", ".rb", ".php", ".ex", ".exs", ".cs", ".swift", ".c", ".h", ".cc",
    ".cpp", ".hpp", ".scala", ".sh", ".ps1", ".sql", ".vue", ".svelte",
}

DOC_FILES = (
    "README.md", "README.rst", "CONTRIBUTING.md", "ARCHITECTURE.md", "CHANGELOG.md",
    "AGENTS.md", "CLAUDE.md", "TASK.md", "HANDOFF.md", "LOG.md", "ISSUES.md",
)

MAX_SCAN_BYTES = 400_000       # a generated bundle is not source; do not read it all
MAX_UNITS = 12                 # one dispatch per unit, and a fan-out has a ceiling
# Above this many files, a top-level directory is split by its own children. Set
# at 8 because that is roughly where one agent stops being able to trace a path
# end to end and starts skimming -- and a skimmed unit reports confidently.
SPLIT_UNIT_AT = 8


def _git(root: Path, *args: str) -> str:
    """stdout, or '' for any failure. Never raises: a repo with no commits, no
    git binary, or a detached HEAD must degrade to 'unknown', not to a crash."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root),
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def layer_owned(root: Path) -> set[str]:
    """Paths belonging to the capability layer rather than to this repository.

    Read from `.claude/layer-manifest.json`, which `.claude/install.py` writes.
    Empty in the source repo, where the layer IS the repository.

    Without this the guest is measured as the host. Installed into a one-file
    service, the first version of this script reported "25 test files over 26 code
    files (ratio 0.962)" -- its own suites -- and a recon pass whose headline
    number is about the wrong repository is worse than no pass at all, because
    every judgement downstream inherits it.
    """
    try:
        data = json.loads(
            (root / ".claude" / "layer-manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    paths = data.get("paths") if isinstance(data, dict) else None
    return {str(p).replace("\\", "/") for p in paths} if isinstance(paths, list) else set()


def walk(root: Path, exclude: set[str] | None = None) -> list[Path]:
    """Every non-noise file, relative to root. One pass; everything else reuses it.

    `exclude` is the layer's own manifest when there is one. Passed in rather than
    read here so a caller can deliberately measure the layer -- which is what
    happens in the repository that owns it.
    """
    skip = exclude or set()
    out: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.name in NOISE_DIRS or entry.name.startswith(".git"):
                continue
            try:
                if entry.is_dir():
                    stack.append(entry)
                elif entry.is_file():
                    rel = entry.relative_to(root)
                    if rel.as_posix() not in skip:
                        out.append(rel)
            except OSError:
                continue
    return sorted(out)


def stack_of(root: Path, files: list[Path]) -> dict:
    """Languages and the commands this repo probably uses, from its manifests."""
    names = {p.name for p in files if len(p.parts) <= 2}
    languages: list[str] = []
    install: list[str] = []
    test: list[str] = []
    for manifest, language, inst, tst in MANIFESTS:
        if manifest not in names:
            continue
        if language not in languages:
            languages.append(language)
        install.append(inst)
        test.append(tst)

    suffixes = Counter(p.suffix for p in files if p.suffix in CODE_SUFFIXES)
    return {
        "manifests": sorted(n for n in names if n in {m for m, _, _, _ in MANIFESTS}),
        "languages": languages,
        "install_hint": install,
        "test_hint": test,
        "by_extension": dict(suffixes.most_common(8)),
    }


def scan_unfinished(root: Path, files: list[Path]) -> tuple[dict, list[dict]]:
    """Count each marker kind and locate the first 40, so the report is actionable.

    Only files with a code suffix are read. A stray marker in a vendored
    changelog is noise, and reading a 4MB bundle to find one is worse than noise.
    """
    counts: Counter[str] = Counter()
    hits: list[dict] = []
    for rel in files:
        if rel.suffix not in CODE_SUFFIXES:
            continue
        path = root / rel
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if len(line) > 400:
                continue
            for pattern, kind in UNFINISHED:
                if not pattern.search(line):
                    continue
                counts[kind] += 1
                if len(hits) < 40:
                    hits.append({
                        "kind": kind,
                        "at": f"{rel.as_posix()}:{number}",
                        "text": line.strip()[:120],
                    })
                break
    return dict(counts.most_common()), hits


def test_topology(files: list[Path]) -> dict:
    """How many tests there are and where they live -- the single best signal of
    whether a completion claim in this repo can be backed by anything."""
    tests = [p for p in files if TEST_HINTS.search(p.as_posix())
             and p.suffix in CODE_SUFFIXES]
    code = [p for p in files if p.suffix in CODE_SUFFIXES and p not in set(tests)]
    roots = Counter(p.parts[0] for p in tests if len(p.parts) > 1)
    return {
        "test_files": len(tests),
        "code_files": len(code),
        "ratio": round(len(tests) / len(code), 3) if code else 0.0,
        "test_roots": [d for d, _ in roots.most_common(5)],
        "examples": [p.as_posix() for p in tests[:5]],
    }


def git_state(root: Path) -> dict:
    """Branch, remote, recency and churn. Churn is the honest answer to 'where is
    the work happening', and it needs no judgement to compute."""
    log = _git(root, "log", "--format=%h|%ad|%s", "--date=short", "-12")
    commits = [line.split("|", 2) for line in log.splitlines() if "|" in line]
    churn = _git(root, "log", "--since=90.days", "--name-only", "--format=")
    counter: Counter[str] = Counter(
        line.strip() for line in churn.splitlines() if line.strip()
    )
    branches = [
        b.strip().lstrip("* ").split()[0]
        for b in _git(root, "branch", "--format=%(refname:short)").splitlines()
        if b.strip()
    ]
    return {
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD") or None,
        "remotes": [r for r in _git(root, "remote").splitlines() if r],
        "commit_count": _git(root, "rev-list", "--count", "HEAD") or "0",
        "branches": branches[:20],
        "recent": [{"sha": c[0], "date": c[1], "subject": c[2][:80]} for c in commits],
        "hot_files": [{"path": p, "commits": n} for p, n in counter.most_common(10)],
        "uncommitted": len([
            line for line in _git(root, "status", "--porcelain").splitlines() if line
        ]),
    }


def recon_units(files: list[Path], limit: int = MAX_UNITS) -> list[dict]:
    """Partition the tree into subsystems with **disjoint** file sets.

    This is the whole reason a comprehension stage can be afforded: one agent per
    unit, dispatched together, each reading files no other agent reads. The
    partition is by top-level directory because that is the boundary a repository
    already chose for itself, and a partition nobody has to trust is better than a
    smarter one somebody has to check.

    Disjointness is a property of the construction here -- every file lands in
    exactly one bucket, keyed by its first path component -- and
    `tools/test_recon.py` asserts it rather than trusting this sentence.
    """
    buckets: dict[str, list[Path]] = {}
    for rel in files:
        if rel.suffix not in CODE_SUFFIXES and rel.suffix not in {".md", ".json", ".yaml", ".yml", ".toml"}:
            continue
        key = rel.parts[0] if len(rel.parts) > 1 else "<root>"
        buckets.setdefault(key, []).append(rel)

    # Descend one level into any unit big enough that mapping it is a whole job.
    #
    # Partitioning by top-level directory alone is correct but useless on the
    # commonest layout there is: everything under `src/`. Measured on a synthetic
    # 24-file service, the fan-out was one unit of 24 and three of one -- a
    # "parallel" recon that is a single agent reading the entire codebase.
    #
    # Only one level, and only when the split actually helps. Recursing further
    # would trade a partition a reviewer can check for one they cannot, and the
    # ceiling on useful concurrency is the agent cap, not the tree depth.
    for key in sorted(buckets):
        members = buckets[key]
        if key == "<root>" or len(members) <= SPLIT_UNIT_AT:
            continue
        children: dict[str, list[Path]] = {}
        for rel in members:
            # parts[0] is `key`; parts[1] is the child, unless the file sits
            # directly in the unit -- those stay together under `<key>/*`.
            child = rel.parts[1] if len(rel.parts) > 2 else "*"
            children.setdefault(f"{key}/{child}", []).append(rel)
        # A split into one bucket is not a split. Two or more, or leave it whole.
        if len(children) < 2:
            continue
        del buckets[key]
        buckets.update(children)

    ranked = sorted(buckets.items(), key=lambda kv: -len(kv[1]))
    units = []
    for name, members in ranked[:limit]:
        code = [p for p in members if p.suffix in CODE_SUFFIXES]
        units.append({
            "unit": name,
            "files": len(members),
            "code_files": len(code),
            "entry_candidates": [
                p.as_posix() for p in members
                if p.stem in {"main", "index", "app", "cli", "__init__", "mod", "lib"}
            ][:5],
            "sample": [p.as_posix() for p in members[:6]],
        })
    dropped = ranked[limit:]
    if dropped:
        units.append({
            "unit": "<remainder>",
            "files": sum(len(m) for _n, m in dropped),
            "code_files": 0,
            "entry_candidates": [],
            "sample": [n for n, _m in dropped[:8]],
            "_note": (
                f"{len(dropped)} smaller top-level path(s) not given their own "
                f"unit because the fan-out ceiling is {limit}. Named here rather "
                f"than dropped silently -- a truncated sweep that prints nothing "
                f"reads as a complete one."
            ),
        })
    return units


def layer_state(root: Path) -> dict:
    """Whether this repository already uses the capability layer, which decides
    whether `resume.py` has anything to read."""
    plans = sorted((root / "docs" / "plans").glob("*.md")) \
        if (root / "docs" / "plans").is_dir() else []
    return {
        "has_claude_dir": (root / ".claude").is_dir(),
        "has_skills": (root / ".claude" / "skills").is_dir(),
        "has_project_checks": (root / ".claude" / "project-checks.json").is_file(),
        "plans": [p.name for p in plans],
        "docs_present": [d for d in DOC_FILES if (root / d).is_file()],
    }


def gather(root: Path) -> dict:
    owned = layer_owned(root)
    files = walk(root, exclude=owned)
    counts, hits = scan_unfinished(root, files)
    return {
        "root": str(root),
        "file_count": len(files),
        "layer_files_excluded": len(owned),
        "stack": stack_of(root, files),
        "tests": test_topology(files),
        "git": git_state(root),
        "layer": layer_state(root),
        "unfinished_counts": counts,
        "unfinished": hits,
        "units": recon_units(files),
    }


def render(facts: dict) -> str:
    out: list[str] = []
    stack = facts["stack"]
    tests = facts["tests"]
    git = facts["git"]
    layer = facts["layer"]

    out.append(f"root            {facts['root']}")
    excluded = facts.get("layer_files_excluded", 0)
    out.append(f"files           {facts['file_count']}"
               + (f"   ({excluded} capability-layer file(s) excluded -- every "
                  f"number below is this repository's)" if excluded else ""))
    out.append(f"languages       {', '.join(stack['languages']) or 'none detected'}")
    out.append(f"manifests       {', '.join(stack['manifests']) or 'none'}")
    out.append(f"test files      {tests['test_files']} over {tests['code_files']} "
               f"code files (ratio {tests['ratio']})")
    out.append(f"test roots      {', '.join(tests['test_roots']) or 'none found'}")
    out.append(f"branch          {git['branch'] or 'unknown'}"
               f"   remotes: {', '.join(git['remotes']) or 'none'}")
    out.append(f"commits         {git['commit_count']}"
               f"   uncommitted paths: {git['uncommitted']}")
    out.append(f"layer           claude={layer['has_claude_dir']} "
               f"skills={layer['has_skills']} plans={len(layer['plans'])}")
    out.append(f"docs            {', '.join(layer['docs_present']) or 'none'}")

    if facts["unfinished_counts"]:
        pairs = "  ".join(f"{k}={v}" for k, v in facts["unfinished_counts"].items())
        out.append(f"unfinished      {pairs}")
    else:
        out.append("unfinished      no markers found")

    if tests["test_files"] == 0 and tests["code_files"] > 0:
        out.append("")
        out.append("WARNING: code with no tests. Until `\"test\": false` is a stated "
                   "decision in .claude/project-checks.json, the auto-commit will "
                   "refuse every change containing code -- deliberately, because an "
                   "absent check is not a passing one.")

    out.append("")
    out.append(f"recon units ({len(facts['units'])}) -- disjoint, dispatch one agent each:")
    for unit in facts["units"]:
        note = "  " + unit["_note"] if unit.get("_note") else ""
        out.append(f"  {unit['unit']:<24} {unit['files']:>5} files "
                   f"({unit['code_files']} code){note}")

    if facts["unfinished"]:
        out.append("")
        out.append("first unfinished markers:")
        for hit in facts["unfinished"][:12]:
            out.append(f"  {hit['kind']:<16} {hit['at']}")

    if git["hot_files"]:
        out.append("")
        out.append("most-changed files, last 90 days:")
        for hot in git["hot_files"][:6]:
            out.append(f"  {hot['commits']:>3}  {hot['path']}")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--units", action="store_true",
                    help="print only the disjoint recon units, one per line")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"no such directory: {root}", file=sys.stderr)
        return 2

    facts = gather(root)
    if args.as_json:
        print(json.dumps(facts, indent=2))
    elif args.units:
        for unit in facts["units"]:
            print(f"{unit['unit']}\t{unit['files']}\t{unit['code_files']}")
    else:
        print(render(facts))
    return 0


if __name__ == "__main__":
    sys.exit(main())

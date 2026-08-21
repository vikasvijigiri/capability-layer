#!/usr/bin/env python3
"""Rebase-before-push, conflict classification, and a PR body from the plan.

    python tools/git_ops.py rebase-plan --base main --head HEAD
    python tools/git_ops.py rebase-plan --base main --head HEAD --offline
    python tools/git_ops.py pr-body --plan docs/plans/2026-08-10-x.md --tier high

Why this exists
----------------
`git rebase` appears in zero layer files, `--force-with-lease` in zero, conflict
classification is prose in `.claude/skills/delivering/SKILL.md` ("classify them
... resolve only mechanical conflicts"), and a PR body has always come from
`gh pr create --fill`, which is the merged `wip:` checkpoint subject line --
squash-commit noise by `CLAUDE.md`'s own design, not a description of the work.

It reports and composes; it never acts
---------------------------------------
The same shape as `tools/scope.py` and `tools/delivery_check.py`: a pure
decision function reads facts and returns a verdict, an IO seam gathers those
facts with an `offline` escape, and nothing here mutates a ref.

`rebase_plan()` never runs `git rebase`. It simulates the merge `git rebase
<base>` would produce with `git merge-tree --write-tree <base> <head>`, which
composes a tree object and reports -- it touches neither the working tree nor
the index. That is a MERGE simulation, not a commit-by-commit replay, and the
two can differ when a rebase's intermediate commits touch a path their final
state does not; this is named in the returned dict's `reason` rather than
glossed over, because a caller reading `clean` needs to know what was actually
checked.

`classify_conflict()` decides from PATHS, not hunks. `git merge-tree` reports
which files conflict, not which lines; a "the third line disagrees" analysis
would need to parse conflict markers this module never asks git to emit, and a
fabricated confidence there would be worse than the honest, coarser answer.

`pr_body()` composes from the plan's `**Goal:**` line, its `## Progress`
checkboxes, a risk tier, and review findings -- **never from `git log`**. This
repository's commits are `wip:` checkpoints by design
(`stop-finalization/06-artifact-autocommit.py`), and squash-merge collapses them; a PR
body built from that list describes the checkpoints, not the work.

Nothing here pushes, rebases, merges, or force-pushes. `test_process_router.py`
fails any file that acquires `gh pr merge`, unnegated, and this one is in its
scan -- this docstring's every mention of it is a prohibition.

A failed subprocess helper returns `None`, never `""` -- `tools/scope.py` and
`tools/delivery_check.py` both name the same bug: an empty string reads as a
real, empty success, and a command that never ran is a different fact.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `100644 <oid> <stage>\t<path>` -- the conflicted-entry lines `git merge-tree
# --write-tree` prints after the tree oid when it exits 1. Stage 1/2/3 are the
# common ancestor / "ours" / "theirs" copies of the same path, so one real
# conflict emits three lines; capturing the path and deduplicating is what
# turns that into a conflict COUNT rather than a line count.
_CONFLICT_LINE = re.compile(r"^\d+\s+[0-9a-f]+\s+[123]\t(.+)$", re.MULTILINE)

# `**Goal:**` through the next blank line or the next `**`-bold field --
# `docs/plans/*.md`'s own shape, per `tools/analyze.py`'s `REQUIRED_HEADINGS`.
_GOAL_RE = re.compile(r"\*\*Goal:\*\*\s*(.+?)(?:\n\s*\n|\n\*\*)", re.S)

def _load(rel: str, name: str):
    """`importlib`, not an import -- `tools/scope.py`'s pattern for reaching a
    sibling module without turning this file into a package member."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


# `- [x] Task 9 — git operations`. Same box `tools/analyze.py`'s `PROGRESS_RE`
# reads -- `_hooklib.PROGRESS_BOX_PATTERN`, imported as text and extended with
# this module's own title-capture suffix, rather than retyping the box/task-
# number prefix a fourth time.
_hooklib_gitops = _load(".claude/hooks/_hooklib.py", "hooklib_gitops_progress")
_PROGRESS_RE = re.compile(
    getattr(_hooklib_gitops, "PROGRESS_BOX_PATTERN",
            r"^- \[( |x|X)\]\s+Task\s+(\d+)\b") + r"\s*[—\-:]*\s*(.*)$",
    re.MULTILINE,
)


def _migration_patterns() -> list[str]:
    """`_hooklib.MIGRATION_PATH_PATTERNS`, imported -- a copy would drift the
    moment the source table changed, which is the defect `tools/scope.py`
    already names for this exact table."""
    mod = _load(".claude/hooks/_hooklib.py", "hooklib_gitops")
    return list(getattr(mod, "MIGRATION_PATH_PATTERNS", []) or [])


def _shared_patterns() -> list[str]:
    """`parallel_groups.SHARED_PATTERNS`, imported, for the same reason: the
    lockfiles and generated/config files a mechanical conflict lives in."""
    mod = _load("tools/parallel_groups.py", "parallel_groups_gitops")
    return list(getattr(mod, "SHARED_PATTERNS", []) or [])


# No table in this repository lists auth paths on their own --
# `tools/scope.py`'s `SENSITIVE_PATTERNS` mixes auth in with the installer and
# packaging surfaces for a different question (risk TIER, not conflict
# classification), and importing it whole would misclassify a `pyproject.toml`
# conflict as auth-substantive for the wrong reason. Kept local and small.
_AUTH_PATTERNS = [
    "**/auth/**", "**/auth.*", "**/*password*", "**/*credential*",
    "**/*secret*", "**/session*.py", "**/permission*",
]


def _norm(path: str) -> str:
    """Repo-relative, forward slashes, `./` stripped -- `tools/scope.py`'s
    `_norm`, which exists because `lstrip` on a character set silently ate a
    real leading dot once. Kept identical rather than re-derived."""
    out = path.replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out


def _match(path: str, patterns: list[str]) -> bool:
    import fnmatch
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def _run(args: list[str], cwd: Path | None = None, timeout: int = 30) -> str | None:
    """stdout on success (possibly `""`), or `None` on failure. Never `""` for
    a failure -- see the module docstring."""
    try:
        proc = subprocess.run(
            args, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


# --- rebase_plan --------------------------------------------------------------

def _gather_rebase_facts(root: Path, base: str, head: str,
                          offline: bool = False) -> dict:
    """The IO seam. `offline=True` nulls every git-derived fact rather than
    inventing one -- the same escape `tools/scope.py` and
    `tools/delivery_check.py` both use."""
    facts: dict = {"base": base, "head": head}
    facts["base_sha"] = _run(["git", "rev-parse", base], root)
    facts["head_sha"] = _run(["git", "rev-parse", head], root)
    facts["merge_base"] = _run(["git", "merge-base", base, head], root)

    if offline or facts["base_sha"] is None or facts["head_sha"] is None \
            or facts["merge_base"] is None:
        facts["commits"] = None
        facts["conflicts"] = None
        return facts

    log = _run(["git", "log", "--format=%h %s", f"{base}..{head}"], root)
    facts["commits"] = log.splitlines() if log is not None else None

    # `git merge-tree --write-tree` composes a tree object and reports; it
    # writes to neither the working tree nor the index, so this "runs" nothing
    # a rollback would ever need to undo.
    try:
        proc = subprocess.run(
            ["git", "merge-tree", "--write-tree", base, head],
            cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout_default(), check=False,
        )
    except (OSError, subprocess.SubprocessError):
        facts["conflicts"] = None
        return facts

    if proc.returncode == 0:
        facts["conflicts"] = []
    elif proc.returncode == 1:
        facts["conflicts"] = sorted(set(_CONFLICT_LINE.findall(proc.stdout)))
    else:
        # Some other failure (bad refs, no merge base at all): unknown, not
        # clean. Article V -- a fact that could not be established is never
        # reported as the passing case.
        facts["conflicts"] = None

    return facts


def timeout_default() -> int:
    """A named constant rather than a bare `30` at the call site, so a slow
    `merge-tree` on a large repo is one line to change."""
    return 30


def _decide_rebase(facts: dict) -> dict:
    """Pure. facts -> what `git rebase <base>` onto `<head>` WOULD do.

    Four outcomes, each named rather than inferred from a missing key:
    `unknown` (a ref or the simulation could not be established), `no-op`
    (head already contains base), `clean`, `conflict`.
    """
    base_sha = facts.get("base_sha")
    head_sha = facts.get("head_sha")
    merge_base = facts.get("merge_base")

    if base_sha is None or head_sha is None or merge_base is None:
        return {"would": "unknown", "commits": None, "conflicts": None,
                "reason": "the base or head ref could not be resolved"}

    if merge_base == base_sha and base_sha == head_sha:
        return {"would": "no-op", "commits": [], "conflicts": [],
                "reason": "base and head are the same commit"}

    if merge_base == base_sha:
        return {"would": "no-op", "commits": facts.get("commits") or [],
                "conflicts": [],
                "reason": "head already contains base; nothing to replay"}

    commits = facts.get("commits")
    conflicts = facts.get("conflicts")
    if commits is None or conflicts is None:
        return {"would": "unknown", "commits": commits, "conflicts": conflicts,
                "reason": "the commit list or the merge simulation could not "
                          "be established"}

    if conflicts:
        return {"would": "conflict", "commits": commits, "conflicts": conflicts,
                "reason": f"{len(conflicts)} path(s) would conflict "
                          f"(merge simulation, not a commit-by-commit replay)"}

    return {"would": "clean", "commits": commits, "conflicts": [],
            "reason": f"{len(commits)} commit(s) would replay onto "
                      f"{facts.get('base')!r} with no conflicting path "
                      f"(merge simulation, not a commit-by-commit replay)"}


def rebase_plan(root: Path, base: str, head: str = "HEAD",
                 offline: bool = False) -> dict:
    """What `git rebase <base>` onto `<head>` WOULD do. Never runs one.

    Composes `_gather_rebase_facts` (IO) and `_decide_rebase` (pure) -- the
    two are exposed separately so a caller, or a test, can hand `_decide_rebase`
    a crafted `facts` dict without touching git at all.
    """
    facts = _gather_rebase_facts(Path(root), base, head, offline=offline)
    return _decide_rebase(facts)


# --- classify_conflict ---------------------------------------------------

def classify_conflict(paths: list[str] | None) -> dict:
    """Pure. Conflicting PATHS -> mechanical or substantive, never guessed.

    A lockfile or generated/config file (`parallel_groups.SHARED_PATTERNS`) is
    mechanical. A path under a migration (`_hooklib.MIGRATION_PATH_PATTERNS`)
    or an auth path is substantive and escalates. **Any path matching neither
    table is also substantive** -- an unclassified conflict defaults to the
    safe outcome, the same veto-list discipline `tools/scope.py` uses for
    `undetermined`: an unmapped fact is never treated as the cheap answer.

    Decided path-by-path, not by hunk content -- see the module docstring for
    why: `git merge-tree` reports which files conflict, not which lines, and
    this module only reads what git actually emits.
    """
    if not paths:
        return {"class": "unknown", "escalate": True, "matched": [],
                "reason": "no conflicting paths given -- nothing to classify"}

    norm = [_norm(p) for p in paths]
    mechanical_patterns = _shared_patterns()
    substantive_patterns = _migration_patterns() + _AUTH_PATTERNS

    substantive_hits = [p for p in norm if _match(p, substantive_patterns)]
    if substantive_hits:
        return {"class": "substantive", "escalate": True,
                "matched": substantive_hits,
                "reason": "under a migration or auth path -- escalates rather "
                          "than being resolved automatically"}

    unmatched = [p for p in norm if not _match(p, mechanical_patterns)]
    if unmatched:
        return {"class": "substantive", "escalate": True, "matched": unmatched,
                "reason": "not every conflicting path is a known lockfile or "
                          "generated file -- an unclassified conflict "
                          "escalates, it is not assumed mechanical"}

    return {"class": "mechanical", "escalate": False, "matched": norm,
            "reason": "every conflicting path is a known lockfile or "
                      "generated file"}


# --- pr_body ---------------------------------------------------------------

def pr_body(plan_text: str, tier: str | None = None,
            findings: list | None = None) -> str:
    """Pure. Composes a PR body from the PLAN, a risk tier, and review
    findings -- never from `git log`. See the module docstring for why the
    commit list is excluded on purpose.

    `findings` is either `None`, a list of strings, or a list of
    `delivery_check`/`code-review`-shaped dicts carrying `severity`/`code` or
    `severity`/`finding` (or `summary`) keys -- both are read defensively so a
    caller does not have to normalise its shape first.
    """
    goal_m = _GOAL_RE.search(plan_text or "")
    goal = goal_m.group(1).strip() if goal_m else \
        "(no `**Goal:**` line found in the plan)"

    ticked = [
        f"Task {num}: {title.strip()}" if title.strip() else f"Task {num}"
        for mark, num, title in _PROGRESS_RE.findall(plan_text or "")
        if mark.lower() == "x"
    ]

    lines = ["## Goal", "", goal, "", "## Completed", ""]
    lines += [f"- {t}" for t in ticked] if ticked else \
        ["- (no ticked `## Progress` boxes found in the plan)"]

    lines += ["", "## Risk tier", "", tier or "unknown"]

    lines += ["", "## Review findings", ""]
    if findings:
        for f in findings:
            if isinstance(f, dict):
                label = f.get("severity") or f.get("class") or "?"
                what = f.get("code") or f.get("file") or ""
                detail = f.get("finding") or f.get("summary") or f.get("reason") or ""
                lines.append(f"- [{label}] {what}: {detail}".rstrip(": "))
            else:
                lines.append(f"- {f}")
    else:
        lines.append("- none reported")

    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser("rebase-plan", help="what a rebase would do -- never runs one")
    rp.add_argument("--base", required=True)
    rp.add_argument("--head", default="HEAD")
    rp.add_argument("--root", default=".")
    rp.add_argument("--offline", action="store_true")
    rp.add_argument("--json", action="store_true", dest="as_json")

    pb = sub.add_parser("pr-body", help="compose a PR body from a plan file")
    pb.add_argument("--plan", required=True)
    pb.add_argument("--tier", default=None)

    args = ap.parse_args(argv)

    if args.cmd == "rebase-plan":
        result = rebase_plan(Path(args.root).resolve(), args.base, args.head,
                              offline=args.offline)
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"rebase-plan: {args.head} onto {args.base} -> {result['would']}")
            print(f"  {result['reason']}")
            for c in (result.get("conflicts") or []):
                print(f"  [conflict] {c}")
        # 0 clean/no-op · 1 conflict · 2 unknown -- 2 is not 0, Article V.
        return {"clean": 0, "no-op": 0, "conflict": 1}.get(result["would"], 2)

    if args.cmd == "pr-body":
        plan_path = Path(args.plan)
        try:
            text = plan_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"cannot read {plan_path}: {exc}", file=sys.stderr)
            return 2
        print(pr_body(text, tier=args.tier))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())

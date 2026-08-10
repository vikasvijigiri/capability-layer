#!/usr/bin/env python3
"""Is this change small or major — computed, so the answer is not a mood.

    python tools/scope.py                  # working tree vs its merge-base
    python tools/scope.py --base main
    python tools/scope.py --offline        # no git; the verdict is undetermined
    python tools/scope.py --json

Why a veto list and not a score
-------------------------------
`no-slop`, `code-review` and the test tier all want to know how much of the
repository a change deserves. Judged, the answer under deadline pressure is
always "small". So it is computed from a **veto list**: any clause firing forces
`major`, and every firing clause is named, so "why was this major" is readable
off the output.

A weighted score was rejected. It lets two cheap signals outvote one expensive
one, and it turns an auditable decision into arithmetic nobody can check --
`test_scope.py` proves each clause by inverting it alone, which is a test a score
cannot support.

It reports; it never decides
----------------------------
The same shape as `resume.py`, `analyze.py`, `git_identity.py` and
`delivery_check.py`. Nothing here runs a check, narrows a suite or skips a sweep;
callers read the verdict and own what they do with it.

Undetermined is not small
-------------------------
Article V of `.claude/constitution.md`. A clause that could not be evaluated is
reported in `skipped` and the verdict becomes `undetermined`, never `small` --
because `small` licenses running fewer checks, and a fact nobody could establish
is not permission to check less. `main()` exits 2 for that, and 2 is not 0.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Measured, not picked. Across the units this repository shipped between
# 2026-08-01 and 2026-08-10, single-concern changes ran 1-6 code files; the two
# that ran wider were the framing merge (14) and the hook deletion (19), both of
# which every reader would call major on sight. 8 sits in the gap between those
# populations. Re-measure before lowering it; do not lower it because a change
# you are in the middle of tripped it.
VOLUME_LIMIT = 8

# A code file, for the volume and spread clauses. A docs-only change of forty
# files is not a major change, and counting it as one would make the tool fire
# on exactly the work it should ignore.
CODE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb",
                 ".java", ".kt", ".cs", ".php", ".ex", ".exs", ".sh", ".ps1"}

# Files that decide what fires, rather than what runs. A change here alters the
# behaviour of every later change, so it is major regardless of its size --
# `.claude/skills/**` is deliberately absent: editing one skill's prose is the
# commonest small change in this repository.
CONTROL_PATTERNS = [
    ".claude/hooks/*", ".claude/hooks/**", ".claude/agents/*",
    ".claude/agents/**", ".claude/workflow.md", ".claude/constitution.md",
    ".claude/settings.json",
]

CLAUSES = ("shared-surface", "control-surface", "volume", "spread", "unmapped")


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _migration_patterns() -> list[str]:
    """`_hooklib`'s table, imported. A copy would drift the moment it changed."""
    mod = _load(".claude/hooks/_hooklib.py", "hooklib_scope")
    return list(getattr(mod, "MIGRATION_PATH_PATTERNS", []) or [])


def _shared_patterns() -> list[str]:
    """`parallel_groups`' table, imported, for the same reason."""
    mod = _load("tools/parallel_groups.py", "parallel_groups_scope")
    return list(getattr(mod, "SHARED_PATTERNS", []) or [])


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./") if path.startswith("./") \
        else path.replace("\\", "/")


def _match(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def _is_code(path: str) -> bool:
    return Path(path).suffix.lower() in CODE_SUFFIXES


def classify(facts: dict) -> dict:
    """Pure. facts -> {scope, fired, skipped, considered, detail}.

    `facts["paths"]` is a list of repository-relative paths, or None when it
    could not be established. `facts["test_map"]` maps a glob to the check
    command that covers it, or None when no map is configured yet.
    """
    paths_in = facts.get("paths")
    test_map = facts.get("test_map")

    fired: list[str] = []
    skipped: list[str] = []
    detail: dict[str, list[str]] = {}

    if paths_in is None:
        # No clause can be evaluated, so none is claimed to have passed.
        return {"scope": "undetermined", "fired": [], "skipped": list(CLAUSES),
                "considered": list(CLAUSES),
                "detail": {}, "reason": "the changed paths could not be established"}

    paths = [_norm(p) for p in paths_in]
    if not paths:
        return {"scope": "undetermined", "fired": [], "skipped": list(CLAUSES),
                "considered": list(CLAUSES), "detail": {},
                "reason": "no changed paths -- nothing to classify"}

    code = [p for p in paths if _is_code(p)]

    shared = [p for p in paths
              if _match(p, _shared_patterns() + _migration_patterns())]
    if shared:
        fired.append("shared-surface")
        detail["shared-surface"] = shared

    control = [p for p in paths if _match(p, CONTROL_PATTERNS)]
    if control:
        fired.append("control-surface")
        detail["control-surface"] = control

    if len(code) > VOLUME_LIMIT:
        fired.append("volume")
        detail["volume"] = [f"{len(code)} code files > {VOLUME_LIMIT}"]

    containers = sorted({p.split("/")[0] for p in code if "/" in p})
    if len(containers) > 1:
        fired.append("spread")
        detail["spread"] = containers

    if test_map is None:
        skipped.append("unmapped")
    else:
        unmapped = [p for p in code
                    if not any(fnmatch.fnmatch(p, g) for g in test_map)]
        if unmapped:
            fired.append("unmapped")
            detail["unmapped"] = unmapped

    if fired:
        verdict = "major"
        reason = "vetoed by: " + ", ".join(fired)
    elif skipped:
        # Nothing fired, but not every clause ran. Reporting `small` here is the
        # silent degradation Article V forbids.
        verdict = "undetermined"
        reason = "no clause fired, but these could not be evaluated: " + \
                 ", ".join(skipped)
    else:
        verdict = "small"
        reason = f"none of {len(CLAUSES)} clauses fired"

    return {"scope": verdict, "fired": fired, "skipped": skipped,
            "considered": list(CLAUSES), "detail": detail, "reason": reason}


def _run(args: list[str], cwd: Path) -> str | None:
    """None on failure. `""` means a real, empty success -- see delivery_check."""
    try:
        out = subprocess.run(args, cwd=str(cwd), capture_output=True,
                             text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def gather(root: Path, base: str | None = None, offline: bool = False) -> dict:
    """The IO seam. `offline=True` nulls every fact rather than inventing one."""
    root = Path(root)
    test_map = None
    cfg = root / ".claude" / "project-checks.json"
    if cfg.is_file():
        try:
            test_map = json.loads(cfg.read_text(encoding="utf-8")).get("test_map")
        except (ValueError, OSError):
            test_map = None

    if offline:
        return {"paths": None, "test_map": test_map, "base": base}

    paths: list[str] = []
    if base:
        merge_base = _run(["git", "merge-base", base, "HEAD"], root) or base
        diffed = _run(["git", "diff", "--name-only", merge_base], root)
        if diffed is None:
            return {"paths": None, "test_map": test_map, "base": base}
        paths.extend(ln for ln in diffed.splitlines() if ln.strip())

    # Uncommitted work counts: the sweep and the review read the tree, not the
    # last commit.
    status = _run(["git", "status", "--porcelain=v1", "-uall"], root)
    if status is None and not base:
        return {"paths": None, "test_map": test_map, "base": base}
    for line in (status or "").splitlines():
        if len(line) > 3:
            paths.append(line[3:].strip().strip('"').split(" -> ")[-1])

    return {"paths": sorted(set(paths)), "test_map": test_map, "base": base}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=None)
    ap.add_argument("--root", default=".")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    result = classify(gather(root, args.base, offline=args.offline))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"scope: {result['scope']}  --  {result['reason']}")
        for clause in result["fired"]:
            for item in result["detail"].get(clause, []):
                print(f"  [{clause}] {item}")
        for clause in result["skipped"]:
            print(f"  [{clause}] NOT EVALUATED")

    # 0 small · 1 major · 2 undetermined. `major` is not an error, so it is not
    # 2; `undetermined` is the one a caller must never read as permission.
    return {"small": 0, "major": 1}.get(result["scope"], 2)


if __name__ == "__main__":
    sys.exit(main())

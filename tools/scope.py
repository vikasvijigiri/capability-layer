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

# --- risk tier ---------------------------------------------------------------
#
# `small`/`major` answers "how much of the repo does this change deserve to be
# checked against". `low`/`medium`/`high` answers a different question -- "how
# much of the pipeline should trust automation with it" -- and four things read
# it: whether a deep security pass runs, whether a merge may be narrowed, what
# shape a release takes, and whether Gate 2 may auto-approve.
#
# Same veto principle, so the answer stays auditable: a tier is forced by a named
# clause, never averaged. The tiers are ordered and the highest forced wins.
TIERS = ("low", "medium", "high")

# Paths where a mistake is not merely a bug. Auth and credentials because the
# blast radius is other people's data; the installer and the packaging because a
# defect there lands in every repository that takes an upgrade, which is the one
# failure this project can cause outside itself.
SENSITIVE_PATTERNS = [
    "**/auth/**", "**/auth.*", "**/*password*", "**/*credential*",
    "**/*secret*", "**/session*.py", "**/permission*",
    ".claude/install.py", "capability_layer/**", "pyproject.toml",
    ".github/workflows/**",
]

# Which clause forces which tier. A clause absent from here contributes nothing
# on its own -- `unmapped` is deliberately absent, because an unmapped path is a
# gap in the test map rather than a fact about the change's danger.
CLAUSE_TIER = {
    "shared-surface": "high",     # migrations and lockfiles: least reversible
    "control-surface": "high",    # changes what fires for every later change
    "volume": "medium",
    "spread": "medium",
}


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
    """Repo-relative, forward slashes, no `./` prefix -- and the dot KEPT.

    `lstrip("./")` was the first version and it is the same defect this plan's
    Task 1 removed from `parallel_groups.normalise`: `lstrip` takes a character
    SET, so `./.claude/settings.json` became `claude/settings.json` and matched
    no pattern at all. Measured: `classify(["./.claude/hooks/_hooklib.py"])`
    fired only `unmapped`, while the identical path without the prefix fired
    `control-surface` too -- so a control surface was invisible and the change
    could classify `small`.

    Latent rather than live, because `gather()` sources paths from
    `git diff --name-only` and `git status --porcelain`, neither of which emits
    a `./` prefix. `classify()` is public and is what every consumer calls, so
    it is fixed rather than documented.
    """
    out = path.replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out


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


def tier(verdict: dict, paths=None) -> dict:
    """Pure. A `classify()` verdict (+ its paths) -> {tier, forced_by, reason}.

    Ordered veto, not an average: every clause that forces a tier is named, and
    the highest one wins. `undetermined` is `high`, never `low` -- Article V,
    and the tier is what decides whether a human may be skipped at Gate 2, which
    is the last place to guess.
    """
    if verdict.get("scope") == "undetermined":
        return {"tier": "high", "forced_by": ["undetermined"],
                "reason": "the change could not be classified, and an "
                          "unclassifiable change is never low-risk"}

    forced: dict[str, str] = {}
    for clause in verdict.get("fired", []):
        if clause in CLAUSE_TIER:
            forced[clause] = CLAUSE_TIER[clause]

    sensitive = [p for p in (_norm(p) for p in (paths or []))
                 if _match(p, SENSITIVE_PATTERNS)]
    if sensitive:
        forced["sensitive-surface"] = "high"

    if not forced:
        return {"tier": "low", "forced_by": [],
                "reason": "no clause forces a tier above low",
                "sensitive": []}

    highest = max(forced.values(), key=TIERS.index)
    names = sorted(k for k, v in forced.items() if v == highest)
    return {"tier": highest, "forced_by": names,
            "reason": f"{highest} forced by: {', '.join(names)}",
            "sensitive": sensitive}


def plan_paths(plan: Path) -> list[str] | None:
    """The paths a PLAN declares, for tiering work that has no diff yet.

    Sourced from `_hooklib.declared_paths`, which parses the plan's own
    `- Create:` / `- Modify:` / `**Files:**` lines. Reused rather than
    re-parsed: the minimal-diff gate and the risk tier must agree on what a plan
    declares, or a file can be in scope for one and not the other.

    None when the plan cannot be read, which tiers `high` rather than `low`.
    """
    mod = _load(".claude/hooks/_hooklib.py", "hooklib_tier")
    if mod is None or not plan.is_file():
        return None
    try:
        text = plan.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    declared: set = set()
    for m in mod.DECLARE_LINE.finditer(text):
        value = m.group(1)
        import re as _re
        value = _re.split(r"\s+(?:—|–|--)\s+|\s+#\s+", value, maxsplit=1)[0]
        for raw in _re.findall(r"`([^`\n]+)`", value):
            token = raw.strip().rstrip(",;.").replace("\\", "/").split(":", 1)[0]
            if token and not token.endswith("/") and " " not in token:
                declared.add(token)
    return sorted(declared)


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
    ap.add_argument("--plan", default=None,
                    help="tier a PLAN's declared paths instead of a diff -- "
                         "this is how work is tiered before it exists")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()

    if args.plan:
        declared = plan_paths(Path(args.plan))
        facts = gather(root, args.base, offline=True)
        facts["paths"] = declared
        result = classify(facts)
        risk = tier(result, declared)
        if args.json:
            print(json.dumps({**result, **risk, "paths": declared}, indent=2))
        else:
            print(f"risk: {risk['tier']}  --  {risk['reason']}")
            print(f"scope: {result['scope']}  --  {result['reason']}")
            for path in risk.get("sensitive") or []:
                print(f"  [sensitive-surface] {path}")
            print(f"  {len(declared or [])} path(s) declared by the plan")
        # 0 low · 1 medium · 2 high. Ordered, so a caller can threshold on it.
        return TIERS.index(risk["tier"])

    # Gathered ONCE. Calling it twice ran the whole git probe a second time for
    # a value already in hand, and worse, it could disagree with itself: the two
    # calls are separated by a classify, so a file written in between would make
    # the tier and the scope describe different trees.
    facts = gather(root, args.base, offline=args.offline)
    result = classify(facts)
    risk = tier(result, facts.get("paths"))

    if args.json:
        print(json.dumps({**result, **risk}, indent=2))
    else:
        print(f"scope: {result['scope']}  --  {result['reason']}")
        print(f"risk:  {risk['tier']}  --  {risk['reason']}")
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

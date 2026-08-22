#!/usr/bin/env python3
"""Objective 26 (low-coupling / composable) -- import-independence contract.

A stdlib `ast` import-graph walk, mirroring `import-linter`'s `independence`
contract type and its `ignore_imports` allowlist mechanism (confirmed live
this session -- see `docs/research/2026-08-22-cluster-d-b-grounding-refresh.md`).

Two declared contracts, non-test source only -- `tools/test_*.py` and
`tools/conftest.py` are excluded because dynamically loading a hook or tool
module to test it is their entire job, not a coupling defect:

  1. Hook families (each top-level `.claude/hooks/<family>/` directory) must
     not import or `_load()` another family's module -- only `_hooklib.py`
     and `_projectchecks.py` are shared.
  2. `tools/*.py` must not import or `_load()` a `.claude/hooks/**` module
     except `_hooklib.py`.

Detects two things per file: real `import`/`from X import Y` statements
(via `ast.Import`/`ast.ImportFrom`) AND this repo's own dynamic-load idiom,
`_load(<path-expression>, "name")` (via `ast.Call`), since that pattern
bypasses static imports entirely -- the mechanism `_load()` allowlist
below exists to name.

Report only -- exits 0 regardless.

Run: python tools/test_import_independence.py
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / ".claude" / "hooks"
TOOLS_DIR = ROOT / "tools"
SHARED_HOOK_FILES = {"_hooklib.py", "_projectchecks.py"}

# Files using this repo's accepted verbatim-copy-per-file `_load(rel, name)`
# importlib helper -- an intentional pattern, not something to centralize.
# Citation: docs/plans/2026-08-20-router-progress-consistency.md's Grounding
# ("one _load(rel, name) importlib helper... one copy per file, an accepted
# existing pattern -- not something this plan centralizes, that would be
# scope creep"). Confirmed live this session: `grep -rl "^def _load(" tools/*.py`.
LOAD_HELPER_ALLOWLIST = {
    "tools/analyze.py", "tools/budget.py", "tools/chain.py", "tools/git_ops.py",
    "tools/loop.py", "tools/parallel_groups.py", "tools/resume.py",
    "tools/scope.py", "tools/security_gate.py", "tools/test_hooks.py",
}


def is_test_or_conftest(path: Path) -> bool:
    return path.name.startswith("test_") or path.name == "conftest.py"


def hook_family(path: Path) -> str | None:
    """The family directory name, or None for a top-level shared hook file."""
    try:
        rel = path.relative_to(HOOKS_DIR)
    except ValueError:
        return None
    return rel.parts[0] if len(rel.parts) > 1 else None


def string_literals_in_call(node: ast.Call) -> list[str]:
    """Every string constant reachable from a `_load(...)` call's arguments,
    including through a `Path / "seg" / "seg"` BinOp chain -- good enough to
    name the target file, not a full path resolver."""
    found: list[str] = []

    def walk(n: ast.AST) -> None:
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            found.append(n.value)
        for child in ast.iter_child_nodes(n):
            walk(child)

    for arg in node.args:
        walk(arg)
    return found


def find_load_targets(tree: ast.AST) -> list[str]:
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name == "_load" and node.args:
                targets.append("/".join(string_literals_in_call(node)))
    return targets


def find_import_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def check_hook_independence() -> tuple[int, list[str]]:
    violations: list[str] = []
    declared = 0
    for path in sorted(HOOKS_DIR.rglob("*.py")):
        if is_test_or_conftest(path) or "__pycache__" in path.parts:
            continue
        family = hook_family(path)
        if family is None:
            continue  # shared top-level file, not a family member
        declared += 1
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
        for name in find_import_names(tree) + find_load_targets(tree):
            for other_family in (p.name for p in HOOKS_DIR.iterdir()
                                  if p.is_dir() and p.name not in ("state", "__pycache__")):
                if other_family == family:
                    continue
                if other_family in name and any(sf.replace(".py", "") not in name
                                                 for sf in SHARED_HOOK_FILES):
                    violations.append(f"{rel} -> {other_family} (via {name!r})")
    return declared, violations


def check_tools_hooks_independence() -> tuple[int, list[str]]:
    violations: list[str] = []
    declared = 0
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if is_test_or_conftest(path):
            continue
        declared += 1
        rel = path.relative_to(ROOT).as_posix()
        allowed = rel in LOAD_HELPER_ALLOWLIST
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
        for name in find_import_names(tree) + find_load_targets(tree):
            if "hooks" not in name or "_hooklib" in name:
                continue
            if allowed:
                continue  # named, cited exception -- see LOAD_HELPER_ALLOWLIST
            violations.append(f"{rel} -> .claude/hooks (via {name!r}), not in LOAD_HELPER_ALLOWLIST")
    return declared, violations


def main() -> int:
    hook_declared, hook_violations = check_hook_independence()
    tools_declared, tools_violations = check_tools_hooks_independence()

    print(f"objective 26 (import independence): "
          f"{hook_declared} hook file(s), {tools_declared} tools/*.py file(s) checked")
    print(f"  contract 1 (hook families independent): "
          f"{len(hook_violations)} violation(s)")
    for v in hook_violations:
        print(f"    {v}")
    print(f"  contract 2 (tools/* <-> hooks only via _hooklib): "
          f"{len(tools_violations)} violation(s)")
    for v in tools_violations:
        print(f"    {v}")
    print(f"  allowlisted _load()-per-file exception: {len(LOAD_HELPER_ALLOWLIST)} file(s), "
          "citation: docs/plans/2026-08-20-router-progress-consistency.md")
    print("\nReport only -- exits 0 regardless.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

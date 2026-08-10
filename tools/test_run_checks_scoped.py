#!/usr/bin/env python3
"""A scoped run cannot print PASS, cannot hide a skip, and refuses a major change.

Why this suite exists
---------------------
`--scoped` makes a run cheaper by running fewer checks. Every rule around it is
there because "cheaper" is one edit away from "reported green on less evidence",
and that failure is silent: the run is shorter, greener and indistinguishable
from a full one in the line anybody quotes.

So the three properties are asserted directly rather than inferred from a live
run -- and deliberately so, because the live verification the plan originally
specified **cannot pass on the change that implements it**: this change is
`major` by `scope.py`'s own veto list, so `--scoped` correctly refuses it. A
verification that can only be run somewhere else is not a verification, and the
honest fix is a suite that can run anywhere.

Run: python tools/test_run_checks_scoped.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, rel
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rc = load("tools/run_checks.py", "run_checks_mod")
pc = load(".claude/hooks/_projectchecks.py", "projectchecks_mod")

# --- the verdict word ---------------------------------------------------------
#
# The single most important property. `PASS` is what a reader copies into a
# report; a scoped run must not be able to produce it.
src = (ROOT / "tools" / "run_checks.py").read_text(encoding="utf-8")
check("a scoped run has its own verdict word",
      rc.PARTIAL_VERDICT == "PARTIAL PASS", rc.PARTIAL_VERDICT)
scoped_body = src.split("def run_scoped", 1)[1].split("\ndef ", 1)[0]
check("run_scoped never prints a bare PASS on success",
      '"PASS: "' not in scoped_body.replace('("PASS: " if ok else "FAIL: ")', ""),
      "the escalation path may print PASS -- it ran the full tier -- but the "
      "narrowed path must not")

# --- selection: what runs, what is named as skipped ---------------------------
RESOLVED = [
    ("lint", "python -m ruff check ."),
    ("typecheck", "python -m mypy"),
    ("test", "python tools/test_scope.py"),
    ("test", "python tools/test_loop.py"),
    ("test", "python tools/test_worktree.py"),
]
VERDICT = {
    "paths": ["tools/scope.py"],
    "test_map": {"tools/scope.py": "python tools/test_scope.py"},
}

to_run, skipped, unmapped = rc.scoped_selection(pc, RESOLVED, VERDICT)
run_cmds = [c for _k, c in to_run]
skip_cmds = [c for _k, c in skipped]

check("the mapped suite runs", "python tools/test_scope.py" in run_cmds, str(run_cmds))
check("the unmapped test suites are skipped, not silently dropped",
      {"python tools/test_loop.py", "python tools/test_worktree.py"} <= set(skip_cmds),
      str(skip_cmds))
check("typecheck is never narrowed -- whole-tree checks that stay whole-tree "
      "cost seconds; narrowing them saves nothing and hides findings",
      "python -m mypy" in run_cmds)
# `VERDICT["paths"]` names `tools/scope.py`, a real python file -- so this
# fixture exercises lint narrowing too, not just test narrowing.
check("lint IS narrowed here, because the changed path is a real python file",
      "python -m ruff check tools/scope.py" in run_cmds
      and "python -m ruff check ." not in run_cmds,
      str(run_cmds))
check("the tree-wide lint command it replaced is named as skipped, not "
      "silently dropped",
      "python -m ruff check ." in skip_cmds, str(skip_cmds))
check("every resolved check is either run or named as skipped, plus the "
      "narrowed lint's own tree-wide remainder",
      len(to_run) + len(skipped) == len(RESOLVED) + 1,
      f"{len(to_run)} + {len(skipped)} != {len(RESOLVED)} + 1")
check("nothing is unmapped when every path is mapped", unmapped == [], str(unmapped))

# --- lint narrowing: a subset of the tree-wide run, and its remainder named --
#
# ruff's own S rules run over the whole tree; the point here is a narrower
# VIEW for a `small` change, not a replacement of that gate -- the tree-wide
# command must stay exactly what the full tier runs.
py_files_here = {
    str(p.relative_to(ROOT)).replace("\\", "/")
    for p in ROOT.rglob("*.py")
    if ".git" not in p.relative_to(ROOT).parts
    and ".worktrees" not in p.relative_to(ROOT).parts
}
lint_targets = rc.scoped_lint_targets(
    ["tools/run_checks.py", "tools/test_run_checks_scoped.py",
     "docs/notes.txt", "does/not/exist.py"])
check("scoped lint keeps only changed paths that are real python source",
      set(lint_targets) == {"tools/run_checks.py", "tools/test_run_checks_scoped.py"},
      str(lint_targets))
check("the scoped lint set is a subset of the tree-wide one",
      set(lint_targets) <= py_files_here, str(set(lint_targets) - py_files_here))

to_run_l, skipped_l, _ = rc.scoped_selection(
    pc, [("lint", "python .claude/hooks/check_config_json.py")],
    {"paths": ["tools/run_checks.py"], "test_map": VERDICT["test_map"]})
check("a lint command with no tree-wide `.` marker cannot be narrowed and "
      "still runs in full, rather than vanishing",
      ("lint", "python .claude/hooks/check_config_json.py") in to_run_l
      and not skipped_l,
      f"to_run={to_run_l} skipped={skipped_l}")

to_run_nopy, skipped_nopy, _ = rc.scoped_selection(
    pc, [("lint", "python -m ruff check .")],
    {"paths": ["docs/notes.txt"], "test_map": VERDICT["test_map"]})
check("with no changed python files, lint runs tree-wide rather than "
      "vanishing silently",
      ("lint", "python -m ruff check .") in to_run_nopy and not skipped_nopy,
      f"to_run={to_run_nopy} skipped={skipped_nopy}")

# --- the map's gaps fail safe -------------------------------------------------
#
# An unmapped code path must escalate to the full tier. Running nothing for it
# would be the silent version of the same gap, and the map is a claim nobody
# verifies.
_, _, unmapped2 = rc.scoped_selection(
    pc, RESOLVED, {"paths": ["src/brand_new.py"], "test_map": VERDICT["test_map"]})
check("an unmapped code path is reported so the caller can escalate",
      unmapped2 == ["src/brand_new.py"], str(unmapped2))
check("the escalation path exists in run_scoped",
      "ESCALATING to the full tier" in scoped_body)

# A non-code path is not an escalation. A changed README maps to nothing and
# must not drag the full tier along behind it every time.
_, _, unmapped3 = rc.scoped_selection(
    pc, RESOLVED, {"paths": ["docs/notes.txt"], "test_map": VERDICT["test_map"]})
check("a non-code unmapped path does not force escalation", unmapped3 == [],
      str(unmapped3))

# --- refusals -----------------------------------------------------------------
for word in ("major", "undetermined"):
    check(f"run_scoped refuses a `{word}` change rather than narrowing it",
          'verdict["scope"] != "small"' in scoped_body)
check("...and the refusal exits 2, not 0", "return 2" in scoped_body)
check("a missing test_map is a refusal, not an empty selection",
      'verdict["test_map"] is None' in scoped_body)

# --- the green ref is never moved here ----------------------------------------
#
# Structural rather than promised: `run_checks.py` contains no ref write at all,
# so a scoped run cannot move one. Asserted because the guarantee is what makes
# `PARTIAL PASS` safe, and a future edit adding a convenience ref-write would
# break it invisibly.
#
# Asserted on the ref WRITE, not on the ref name: the module docstring names
# `refs/uaios/green/<slug>` in order to explain the guarantee, and a substring
# scan for the name failed on the very prose that documents it. A check that
# goes red when you write down why it exists is the wrong check.
check("run_checks.py never writes a green ref",
      "update-ref" not in src,
      "a scoped run must not be able to mark a tree verified")

# --- the map itself is real ---------------------------------------------------
#
# Shape, not judgement. Every command the map names must be a suite the project
# actually registers, or a scoped run silently runs nothing for that path.
cfg = json.loads((ROOT / ".claude" / "project-checks.json").read_text(encoding="utf-8"))
test_map = cfg.get("test_map") or {}
# Every kind, not just `test`. `test_smoke.py` and `test_package.py` are
# registered as the slow-tier `smoke` and `build` kinds, and checking `test`
# alone reported both as unregistered suites -- a finding about the checker, not
# about the repository.
registered: set = set()
for _key, _val in cfg.items():
    if _key.startswith("_") or _key == "test_map":
        continue
    if isinstance(_val, str):
        registered.add(_val)
    elif isinstance(_val, list):
        registered.update(v for v in _val if isinstance(v, str))
# `project-checks.json` is never overwritten by the installer -- it says what
# "the checks pass" means in the target repository, and a fresh copy asserting
# this repo's facts is worse than no file. So a target legitimately has no
# `test_map` at all, and `--scoped` there simply refuses to narrow.
#
# Absent is therefore not a failure and is reported as unmeasured. A map that
# exists and names a command nothing registers still is a failure: that path
# silently runs nothing.
if not test_map:
    print("SKIP: no `test_map` in .claude/project-checks.json -- the scoped tier "
          "has nothing to narrow with here, and refuses rather than guessing; "
          "the map's shape is unmeasured in this repository")
else:
    unknown = sorted({cmd for cmd in test_map.values()
                      if cmd not in registered
                      and not cmd.startswith("python tools/run_checks.py")})
    check("every mapped command is a registered suite", not unknown, str(unknown))
    check("the map documents that its judgement is unproven",
          "_why_test_map" in cfg and "silent" in cfg["_why_test_map"])

# --- the sweep's fourth scope --------------------------------------------------
slop = (ROOT / "tools" / "test_no_slop.py").read_text(encoding="utf-8")
check("the sweep offers a `change` scope",
      '"change"' in slop and "changed_files" in slop)
check("...and its verdict names the scope so a clean result is not over-read",
      "not a repo-wide result" in slop)

# `stdin=DEVNULL` is load-bearing: anything downstream that reaches a hook
# calls `load_payload()`, which blocks on an inherited pipe -- and the hang
# only appears when this suite runs through the tier, never alone.
out = subprocess.run([sys.executable, "tools/test_no_slop.py", "--scope", "change"],
                     cwd=str(ROOT), capture_output=True, text=True,
                     stdin=subprocess.DEVNULL, timeout=300)
check("the change sweep runs and states its scope",
      "scope=change" in out.stdout, out.stdout[-300:] or out.stderr[-300:])

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All scoped-run tests passed")

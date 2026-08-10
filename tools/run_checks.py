#!/usr/bin/env python3
"""One entry point for "do the checks pass", used by everything that asks.

The auto-commit hook, `/verify`, `delivering`, and CI all need the same answer,
and three of those four used to work it out separately. Two sources of truth for
what "green" means is how a passing local run starts coexisting with a refusing
gate and a red pipeline -- so they all call this.

    python tools/run_checks.py                # fast tier: lint, typecheck, test
    python tools/run_checks.py --tier slow    # build, audit, e2e, smoke
    python tools/run_checks.py --tier all

Exit 0 only if every check that ran passed. `--require-test` additionally fails
when the tier ran no test at all, which is the distinction the commit gate turns
on: "everything passed" and "nothing ran" are the same boolean and different
facts.

    python tools/run_checks.py --scoped       # only the suites the change touches

`--scoped` narrows the test set to what `test_map` in
`.claude/project-checks.json` maps the changed paths to. It exists so small work
is cheap, and every rule below exists so cheap never becomes *unmeasured*:

  * it prints **`PARTIAL PASS`, never `PASS`**, and names every suite it skipped;
  * it **refuses** — exit 2 — when `tools/scope.py` calls the change `major` or
    cannot classify it, because narrowing is a decision that needs a fact;
  * an **unmapped** changed path escalates to the full tier rather than running
    nothing, so a gap in the map fails safe;
  * it **never moves `refs/uaios/green/<slug>`**. That ref means the full tier
    passed, and it is written by `post-run/06-artifact-autocommit.py` and
    `tools/loop.py` — neither of which calls this flag — so the guarantee is
    structural rather than a promise made here.

"Fast" must mean "ran fewer checks and said which". It must never mean "reported
green on less evidence".
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / ".claude" / "hooks" / "_projectchecks.py"

# `PASS` is reserved for a run that checked everything the tier names. A scoped
# run has not earned that word, and the difference has to be visible in the one
# line a reader actually copies into a report.
PARTIAL_VERDICT = "PARTIAL PASS"


def load_scope():
    spec = importlib.util.spec_from_file_location("scope_mod", ROOT / "tools" / "scope.py")
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def scoped_selection(pc, resolved: list, verdict: dict) -> tuple[list, list, list]:
    """(to_run, skipped, unmapped) for a scoped run.

    Pure given `resolved` and `verdict`, so the escalation rule is testable
    without running a suite. `test_map` maps a path glob to the check command
    that covers it; a changed path matching no glob is `unmapped`, and an
    unmapped path means the caller must escalate rather than narrow.
    """
    test_map = verdict.get("test_map") or {}
    paths = verdict.get("paths") or []

    wanted: set = set()
    unmapped: list = []
    for path in paths:
        hits = [cmd for glob, cmd in test_map.items() if fnmatch.fnmatch(path, glob)]
        if hits:
            wanted.update(hits)
        elif scope_is_code(path):
            unmapped.append(path)

    to_run, skipped = [], []
    for kind, cmd in resolved:
        # Only the test kind is narrowed. Lint and typecheck are whole-tree by
        # construction and cost seconds; narrowing them would save nothing and
        # would be the first place a scoped run started missing real findings.
        if kind != "test" or cmd in wanted:
            to_run.append((kind, cmd))
        else:
            skipped.append((kind, cmd))
    return to_run, skipped, unmapped


def scope_is_code(path: str) -> bool:
    mod = load_scope()
    suffixes = getattr(mod, "CODE_SUFFIXES", {".py"}) if mod else {".py"}
    return Path(path).suffix.lower() in suffixes


def load_projectchecks():
    spec = importlib.util.spec_from_file_location("_projectchecks", MODULE)
    if spec is None or spec.loader is None:
        print(f"FAIL: cannot load {MODULE}", file=sys.stderr)
        raise SystemExit(2)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_scoped(pc, resolved: list, args) -> int:
    """A narrowed run that can never report `PASS` and never hides what it skipped."""
    mod = load_scope()
    if mod is None:
        print("FAIL: --scoped needs tools/scope.py and it could not be loaded",
              file=sys.stderr)
        return 2

    facts = mod.gather(ROOT, args.base)
    verdict = mod.classify(facts)
    verdict["paths"] = facts.get("paths") or []
    verdict["test_map"] = facts.get("test_map")

    print(f"scope: {verdict['scope']}  --  {verdict['reason']}")

    # Refusing is the point. Narrowing a major change is the one failure this
    # flag could cause that nothing downstream would catch, because the run
    # would be green and shorter and look like a success.
    if verdict["scope"] != "small":
        print(f"REFUSED: --scoped narrows a `small` change only; this one is "
              f"`{verdict['scope']}`. Run the full tier.", file=sys.stderr)
        return 2

    if verdict["test_map"] is None:
        print("REFUSED: --scoped needs a `test_map` in .claude/project-checks.json; "
              "without one there is no basis for narrowing.", file=sys.stderr)
        return 2

    to_run, skipped, unmapped = scoped_selection(pc, resolved, verdict)

    if unmapped:
        # The map's gaps must fail safe. An unmapped path is a path nobody said
        # was covered, and running nothing for it would be the silent version of
        # the same gap.
        print(f"ESCALATING to the full tier: {len(unmapped)} changed path(s) "
              f"match no `test_map` rule -- {', '.join(unmapped[:5])}"
              f"{' …' if len(unmapped) > 5 else ''}")
        ok, detail, ran_test = pc.run_checks(ROOT, kinds=pc.FAST_KINDS)
        print(("PASS: " if ok else "FAIL: ") + detail)
        return 0 if ok else 1

    for kind, cmd in to_run:
        print(f"  running   {kind:10} {cmd}")
    for kind, cmd in skipped:
        print(f"  SKIPPED   {kind:10} {cmd}")
    print()

    failed = []
    for _kind, cmd in to_run:
        if pc.tool_missing(cmd):
            print(f"  (skipped: tool missing) {cmd}")
            continue
        # shell=True to match `_projectchecks.run_checks` exactly: the commands
        # come from the same config and several are shell one-liners. Two
        # runners disagreeing about how a configured command is invoked is the
        # drift this whole file exists to prevent.
        rc = subprocess.run(  # noqa: S602
            cmd, cwd=str(ROOT), shell=True).returncode
        if rc != 0:
            failed.append(cmd)

    if failed:
        print(f"FAIL: {len(failed)} of {len(to_run)} scoped check(s) failed -- "
              + "; ".join(failed))
        return 1

    # Never the word `PASS`. A reader copying this line into a report must not
    # be able to present it as a full run.
    print(f"{PARTIAL_VERDICT}: {len(to_run)} check(s) green, "
          f"{len(skipped)} suite(s) NOT run: "
          + (", ".join(cmd for _k, cmd in skipped) if skipped else "none"))
    print("This is not a full tier. `refs/uaios/green/<slug>` is unmoved, and "
          "only the full tier can move it.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", choices=("fast", "slow", "all"), default="fast")
    ap.add_argument("--require-test", action="store_true",
                    help="fail when the tier ran no test check at all")
    ap.add_argument("--scoped", action="store_true",
                    help="narrow the test set to what the change touches; "
                         "prints PARTIAL PASS and names every skipped suite")
    ap.add_argument("--base", default=None,
                    help="base ref for --scoped; defaults to the working tree")
    args = ap.parse_args()

    pc = load_projectchecks()
    kinds = {"fast": pc.FAST_KINDS, "slow": pc.SLOW_KINDS, "all": pc.ALL_KINDS}[args.tier]

    resolved, disabled = pc.resolve_checks(ROOT, kinds)
    print(f"tier={args.tier}  resolved {len(resolved)} check(s)"
          + (f", disabled: {', '.join(disabled)}" if disabled else ""))
    for kind, cmd in resolved:
        marker = "  (skipped: tool missing)" if pc.tool_missing(cmd) else ""
        print(f"  {kind:10} {cmd}{marker}")
    print()

    if args.scoped:
        return run_scoped(pc, resolved, args)

    ok, detail, ran_test = pc.run_checks(ROOT, kinds=kinds)
    print(("PASS: " if ok else "FAIL: ") + detail)

    if not ok:
        return 1
    if args.require_test and not ran_test:
        print("FAIL: no test check ran -- passing and having nothing to run are "
              "different facts", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

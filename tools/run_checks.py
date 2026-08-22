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
    passed, and `--record-green` refuses before running whenever the tier is not
    `all` or the run is scoped, so the two can never be combined.

    python tools/run_checks.py --tier all --require-test --record-green

`--record-green` is the ref's second writer, added 2026-08-16. The first is
`stop-finalization/06-artifact-autocommit.py`, which refuses past `max_files` by design --
so the largest units, the ones that most need a verified checkpoint, were the
ones that never recorded one, and `resume.py` could not leave `BUILD`. It writes
only after a full tier passed AND a test actually ran; unlike the hook's
best-effort version it reports a failure to record rather than swallowing it.

`--scoped` also narrows **lint** the same way it narrows tests: a whole-tree
ruff invocation is rewritten to check only the changed python files, never by
disabling a rule, and the tree-wide command it replaced is printed as skipped
rather than dropped. The tree-wide run itself is untouched and is still what
the full tier runs — this adds a narrower view for a `small` change, it does
not replace the gate. A lint command with no changed python file to narrow to,
or no recognisable tree-wide shape, still runs in full.

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

# ruff only understands python. Narrowing it to a changed non-python path
# would either error or silently check nothing, so lint narrowing looks for
# this suffix regardless of what `scope.py`'s CODE_SUFFIXES lists for other
# purposes.
LINT_SUFFIXES = {".py"}


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


def scoped_lint_targets(paths: list) -> list:
    """Which changed paths are worth handing to ruff directly.

    Only real python files that still exist qualify -- a deleted file cannot
    be linted, and handing ruff a path that is gone is an error, not a
    narrower run.
    """
    return [p for p in paths
            if Path(p).suffix.lower() in LINT_SUFFIXES and (ROOT / p).is_file()]


def narrow_lint_cmd(cmd: str, targets: list):
    """Rewrite a whole-tree ruff invocation to check only `targets`.

    Only a command ending in the tree-wide `.` marker is recognised --
    `python .claude/hooks/check_config_json.py` and
    `python tools/new_skill_check.py --all` take no path argument in a form
    this function understands, and guessing at their shape risks silently
    dropping a check rather than narrowing one. Returns `None` when it cannot
    narrow, and the caller keeps running the command in full rather than
    losing it.
    """
    if not targets:
        return None
    stripped = cmd.rstrip()
    if not stripped.endswith(" ."):
        return None
    return stripped[: -len(" .")] + " " + " ".join(targets)


def scoped_selection(pc, resolved: list, verdict: dict) -> tuple[list, list, list]:
    """(to_run, skipped, unmapped) for a scoped run.

    Pure given `resolved` and `verdict`, so the escalation rule is testable
    without running a suite. `test_map` maps a path glob to the check command
    that covers it; a changed path matching no glob is `unmapped`, and an
    unmapped path means the caller must escalate rather than narrow.

    Lint is narrowed too, the same way test is: a recognisable tree-wide ruff
    invocation is rewritten to the changed python files, and the tree-wide
    command it replaced is appended to `skipped` -- named, not dropped. That
    tree-wide command is untouched in `resolved` itself and is exactly what
    the full tier still runs; this only changes what THIS scoped run does
    with it. A lint command with nothing to narrow to, or no `.` shape this
    function recognises, runs in full rather than vanishing.
    """
    test_map = verdict.get("test_map") or {}
    paths = verdict.get("paths") or []
    lint_targets = scoped_lint_targets(paths)

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
        if kind == "lint":
            narrowed = narrow_lint_cmd(cmd, lint_targets)
            if narrowed:
                to_run.append((kind, narrowed))
                skipped.append((kind, cmd))
            else:
                to_run.append((kind, cmd))
        # Typecheck is whole-tree by construction and costs seconds; narrowing
        # it would save nothing and would be the first place a scoped run
        # started missing real findings.
        elif kind != "test" or cmd in wanted:
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


GREEN_REF_PREFIX = "refs/uaios/green/"


def record_green(root: Path) -> tuple[str, str]:
    """Point `refs/uaios/green/<slug>` at HEAD. `(ref, error)`, one empty.

    The second writer of this ref, and the reason there is one. Until 2026-08-16
    the only writer was `stop-finalization/06-artifact-autocommit.py`, which refuses past
    `max_files` by design -- so a large unit, exactly the kind that most needs a
    verified checkpoint, never recorded that it went green. `resume.derive_state`
    reads the ref as `checks_green`, finds `None`, and returns `BUILD` before it
    can reach `WAITING_DELIVERY`. Setting the ref by hand on a verified tree
    cleared it immediately: the state machine was sound and the plumbing was not.

    Unlike the hook's version this is NOT best-effort. The hook is a background
    courtesy at the end of a turn; this is a thing someone typed, so a failure to
    record must be visible rather than swallowed.
    """
    proc = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(root),
        capture_output=True, text=True)
    branch = (proc.stdout or "").strip()
    if proc.returncode != 0 or not branch:
        return "", "cannot read the current branch"
    if branch == "HEAD":
        return "", "detached HEAD has no unit to record a green tree for"
    slug = branch[len("feat/"):] if branch.startswith("feat/") else branch
    ref = f"{GREEN_REF_PREFIX}{slug}"
    written = subprocess.run(  # noqa: S603
        ["git", "update-ref", ref, "HEAD"], cwd=str(root),
        capture_output=True, text=True)
    if written.returncode != 0:
        return "", (written.stderr or "git update-ref failed").strip()
    return ref, ""


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
    ap.add_argument("--record-green", action="store_true",
                    help="on a full-tier pass, point refs/uaios/green/<slug> at "
                         "HEAD; refused for any narrower run")
    args = ap.parse_args()

    # Refused before anything runs, so the answer does not depend on the result.
    # `--scoped` prints PARTIAL PASS precisely because it has not earned the
    # word PASS, and the green ref means the FULL tier passed -- a scoped run
    # recording it would launder the weaker claim into the stronger one.
    if args.record_green and (args.scoped or args.tier != "all"):
        print("FAIL: --record-green needs `--tier all`; the ref means the full "
              f"tier passed and this run is {'scoped' if args.scoped else args.tier}",
              file=sys.stderr)
        return 2

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

    if args.record_green:
        if not ran_test:
            print("FAIL: --record-green needs a test check to have run; a tier "
                  "that tested nothing has not verified this tree",
                  file=sys.stderr)
            return 1
        ref, err = record_green(ROOT)
        if err:
            print(f"FAIL: --record-green: {err}", file=sys.stderr)
            return 1
        print(f"recorded {ref} at HEAD -- this tree passed the full tier")
    return 0


if __name__ == "__main__":
    sys.exit(main())

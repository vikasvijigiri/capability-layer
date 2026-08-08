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
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / ".claude" / "hooks" / "_projectchecks.py"


def load_projectchecks():
    spec = importlib.util.spec_from_file_location("_projectchecks", MODULE)
    if spec is None or spec.loader is None:
        print(f"FAIL: cannot load {MODULE}", file=sys.stderr)
        raise SystemExit(2)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", choices=("fast", "slow", "all"), default="fast")
    ap.add_argument("--require-test", action="store_true",
                    help="fail when the tier ran no test check at all")
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

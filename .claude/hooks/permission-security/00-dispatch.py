#!/usr/bin/env python3
"""Run the 4 permission-security checks in one process, on one payload load.

Measured on the build machine before this existed: every `Bash`/`PowerShell`
`PreToolUse` call fired 4 separate Python process launches
(secret-scan, branch-guard, attribution-guard, spend-guard), each paying its
own ~50-150ms interpreter-and-import cost on top of `pre-tool/01-halt-guard.py`'s
own launch. `stop-finalization/00-dispatch.py` already solved the same shape
of problem for `Stop` -- by subprocess-chaining, not by importing -- but a
subprocess chain still pays N cold starts, just serially from one entry point.
This dispatcher goes one step further and actually imports each check as a
function, so the 4 checks share ONE interpreter and ONE payload parse.

Semantics preserved exactly from the 4 separate hook registrations they
replace: Claude Code runs every matching hook to completion and combines
results, most restrictive wins (`deny` beats everything). So every check here
still runs even after an earlier one already found a reason to deny -- this
dispatcher denies once, with every reason that fired, not just the first.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _hooklib import deny, load_payload  # noqa: E402

_MODULES = (
    "01-secret-scan",
    "02-branch-guard",
    "03-attribution-guard",
    "04-spend-guard",
)


def _load(name: str):
    # Filenames start with a digit, which is not a valid module name, so this
    # loads each by file path rather than by `import`.
    import importlib.util
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    payload = load_payload()
    reasons: list[str] = []
    for name in _MODULES:
        try:
            module = _load(name)
            reason = module.check(payload)
        except Exception:
            # One check's own bug must not silently allow through, but must
            # also not wedge every shell call in the session -- fail open on
            # THIS check only, matching each module's own standalone posture.
            # Fail open must still be VISIBLE: the 4 separate hooks this
            # replaced each surfaced a broken check as a nonzero exit and a
            # traceback on stderr (docs/harness-hook-bridge.md's "hook-error
            # notice surfaced to the operator"); silently swallowing the
            # exception here would make a broken secret-scan indistinguishable
            # from a clean one. This does not deny -- only the check's own
            # `reason` return value can do that -- it only makes the failure
            # audible.
            print(f"[permission-security] {name}.py raised and could not run "
                  f"this call's check -- fail-open, not a denial, but the "
                  f"operator should see this:\n{traceback.format_exc()}",
                  file=sys.stderr)
            reason = None
        if reason:
            reasons.append(reason)
    if reasons:
        deny("\n\n".join(reasons))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(0) from None

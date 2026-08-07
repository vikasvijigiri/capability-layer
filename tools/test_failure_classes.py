#!/usr/bin/env python3
"""Tests for _hooklib.classify_failure -- what kind of failure is this.

Before this table existed, every red check spent one of three repair attempts.
A port collision and a type error were indistinguishable to the budget, so
infrastructure noise escalated as though the change were broken, and "repairing"
it meant editing product code to chase a fault that was not in it.

Every fixture below is real tool output, not invented phrasing. A row that only
matches a string someone imagined is a row that will not fire when it matters.

The two assertions that carry the most weight:

  1. **Direction of the default.** Unmatched output must classify as a real
     defect, never as noise. Calling a genuine failure transient retries it
     until the budget is gone and changes nothing.
  2. **deterministic outranks transient.** Output that mentions both must be
     treated as the defect it is.

Run: python tools/test_failure_classes.py
"""

from __future__ import annotations

import importlib.util
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
    assert spec is not None, f"no import spec for {rel}"
    assert spec.loader is not None, f"no loader for {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


hl = load(".claude/hooks/_hooklib.py", "hooklib_fc")


# --- one fixture per row, taken from real tool output -----------------------

CASES = [
    # --- transient: infrastructure, never product code
    ("npm ERR! network request to https://registry.npmjs.org failed, reason: "
     "connect ECONNRESET 104.16.0.1:443", "transient", "retry"),
    ("Error: listen EADDRINUSE: address already in use :::3000", "transient", "retry"),
    ("fatal: unable to access 'https://github.com/x/y.git/': "
     "Could not resolve host: github.com", "transient", "retry"),
    ("API rate limit exceeded for user", "transient", "retry"),
    ("HTTP 429 Too Many Requests", "transient", "retry"),
    ("The process cannot access the file because it is being used by another "
     "process.", "transient", "retry"),
    ("OSError: [Errno 11] Resource temporarily unavailable", "transient", "retry"),
    ("requests.exceptions.ConnectTimeout: connect timed out", "transient", "retry"),

    # --- deterministic: a real defect
    ("src/checkout.ts(42,7): error TS2345: Argument of type 'string' is not "
     "assignable to parameter of type 'number'.", "deterministic", "repair"),
    ("error[E0308]: mismatched types", "deterministic", "repair"),
    ("ModuleNotFoundError: No module named 'requests'", "deterministic", "repair"),
    ("AssertionError: assert 3 == 4", "deterministic", "repair"),
    ("FAILED tests/test_checkout.py::test_retry - assert False",
     "deterministic", "repair"),
    ("=== 2 failed, 104 passed in 8.10s ===", "deterministic", "repair"),
    ("Expected the response to equal 200", "deterministic", "repair"),
    ("./main.go:14:2: undefined: doThing", "deterministic", "repair"),
    ("error TS2307: Cannot find module './missing'", "deterministic", "repair"),
    ("tools/x.py:12:5: F401 `os` imported but unused", "deterministic", "repair"),

    # --- merge: rebase, do not edit
    ("CONFLICT (content): Merge conflict in src/app.ts", "merge", "rebase"),
    ("Automatic merge failed; fix conflicts and then commit the result.",
     "merge", "rebase"),

    # --- security: never retried, never auto-repaired
    ("Auto-commit REFUSED: a credential pattern matched in .env -- secret detected",
     "security", "block"),
    # Assembled at runtime, never written contiguously. This file is scanned by
    # the same credential patterns it tests, and a literal key header here makes
    # the whole repository permanently uncommittable -- which is exactly what
    # happened on the first run of this suite. `test_project_checks.py` documents
    # the identical trap for `AKIA`.
    ("-" * 5 + "BEGIN RSA " + "PRIVATE KEY" + "-" * 5, "security", "block"),
    ("found 3 vulnerabilities: CVE-2024-12345 in lodash", "security", "block"),
    ("npm audit: 1 critical severity vulnerability", "security", "block"),
]

for output, want_kind, want_action in CASES:
    kind, action = hl.classify_failure(output)
    label = output.splitlines()[0][:58]
    check(f"{want_kind:<13} <- {label}", (kind, action) == (want_kind, want_action),
          f"got {(kind, action)}")


# --- the default direction --------------------------------------------------
#
# The expensive mistake is calling a real defect noise. So unmatched output is
# treated as a defect and investigated, never retried.

check("unmatched output is a defect, not noise",
      hl.classify_failure("something nobody has seen before") == ("unknown", "repair"))
check("empty output is a defect, not noise",
      hl.classify_failure("") == ("unknown", "repair"))
check("None-ish input does not raise", hl.classify_failure("") is not None)


# --- priority: a real failure that mentions the network is still real -------

MIXED = ("npm WARN network ECONNRESET retrying...\n"
         "AssertionError: expected 200 to equal 500")
check("deterministic outranks transient in mixed output",
      hl.classify_failure(MIXED)[0] == "deterministic",
      f"got {hl.classify_failure(MIXED)}")

SECURITY_FIRST = "2 failed\n" + "-" * 5 + "BEGIN OPENSSH " + "PRIVATE KEY" + "-" * 5
check("security outranks everything",
      hl.classify_failure(SECURITY_FIRST)[0] == "security",
      f"got {hl.classify_failure(SECURITY_FIRST)}")


# --- budgets ----------------------------------------------------------------

check("security has no budget at all", hl.failure_budget("security") == 0,
      "a credential in a diff is not a thing to have another go at")
check("transient is cheaper than deterministic",
      hl.failure_budget("transient") < hl.failure_budget("deterministic"))
check("an unknown class falls back to the deterministic budget",
      hl.failure_budget("no-such-class") == hl.FAILURE_BUDGETS["unknown"])
check("every class in the table has a budget",
      {k for _, k, _ in hl.FAILURE_CLASSES} <= set(hl.FAILURE_BUDGETS),
      f"missing: {sorted({k for _, k, _ in hl.FAILURE_CLASSES} - set(hl.FAILURE_BUDGETS))}")
check("every budget names a class the table can produce or the default",
      set(hl.FAILURE_BUDGETS) <= {k for _, k, _ in hl.FAILURE_CLASSES} | {"unknown"},
      f"orphaned: {sorted(set(hl.FAILURE_BUDGETS) - {k for _, k, _ in hl.FAILURE_CLASSES} - {'unknown'})}")


# --- the signature, now shared with the loop --------------------------------

check("the same failure with a different count has the same signature",
      hl.failure_signature("3 failed") == hl.failure_signature("2 failed"),
      "a partial fix must not reset the attempt budget")
check("a genuinely different failure has a different signature",
      hl.failure_signature("3 failed") != hl.failure_signature("E501 line too long"))
check("the signature is short and stable",
      len(hl.failure_signature("x")) == 12
      and hl.failure_signature("x") == hl.failure_signature("x"))


# --- the table must not match this repo's own ordinary output ---------------
#
# The gate refuses on a security class, so a pattern that matches a passing
# suite's own words would block every commit until someone worked out why. This
# is the same trap the credential patterns hit on 2026-08-03.

BENIGN = [
    "All project-check tests passed",
    "PASS: 21 check(s) green (lint, test, typecheck)",
    "OK: the report quotes the failing output",
    "104 passed in 8.10s",
    "Checked 63 files. All checks passed!",
    "Success: no issues found in 19 source files",
]
for text in BENIGN:
    kind, _ = hl.classify_failure(text)
    check(f"benign output is not classified security/merge: {text[:44]}",
          kind not in ("security", "merge"), f"got {kind}")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All failure-class tests passed")

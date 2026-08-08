#!/usr/bin/env python3
"""Tests for tools/analyze.py -- the pre-Gate-1 consistency pass.

Driven by two fixtures: one plan that is right and one that is wrong in every
way the checker knows about. The good plan must produce **zero** findings, which
is the assertion that matters most -- a checker that cries about correct work is
one nobody runs, and then it protects nothing.

Run: python tools/test_analyze.py
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
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


az = load("tools/analyze.py", "analyze_mod")

GOOD = """# Checkout retry Implementation Plan

**Goal:** retry a failed checkout once before surfacing an error.

**Source spec:** docs/specs/2026-08-07-checkout-retry-design.md

## Constitution gate
- [x] I Evidence — every task names the command
- [x] II Test first — failing test first
- [x] III Smallest change — no refactor
- [x] IV Reversibility — nothing irreversible here
- [x] V No silent degradation — no checks skipped
- [x] VI Mechanism — the retry cap is asserted by a test
- [x] VII Secrets — none

## File map
- `src/checkout.ts` — owns the retry

## Tasks

### Task 1: retry once on a 5xx

**Purpose:** a transient 5xx does not surface to the user.

**Files:**
- Modify: `src/checkout.ts:submit` — wrap in one retry
- Test: `tests/checkout.test.ts` — covers the retry

**Verification:**
- Run: `npm test -- checkout`
- Expect: 2 passed

**Done when:** a single 5xx is retried and a second is surfaced.
"""

BAD = """# Broken Plan

## Tasks

### Task 1: do the thing

**Files:**
- Modify: `src/does_not_exist.ts` — something

[NEEDS CLARIFICATION: which timeout applies?]

## Constitution gate
- [ ] I Evidence — not ticked and not explained
"""


def exists_good(p: str) -> bool:
    return p in ("src/checkout.ts", "tests/checkout.test.ts")


findings = az.analyze(GOOD, exists=exists_good, slug="checkout-retry")
check("a correct plan produces no findings", findings == [],
      "; ".join(f"{f['code']}:{f['finding']}" for f in findings))

bad = az.analyze(BAD, exists=lambda p: False, slug="checkout-retry")
codes = {f["code"] for f in bad}


def has(code: str, needle: str) -> bool:
    return any(f["code"] == code and needle.lower() in f["finding"].lower() for f in bad)


check("a missing Goal is found", has("structure", "goal"))
check("a missing File map is found", has("structure", "file map"))
check("an unresolved clarification marker is found", has("clarification", "timeout"))
check("an unticked article with no justification is found",
      has("constitution", "complexity tracking"))
check("a task with no Run: command is found", has("untestable", "verification"))
check("a task with no expected result is found", has("untestable", "expected"))
check("a task with no Done when is found", has("untestable", "done when"))
check("a Modify target that does not exist is found",
      has("path", "does_not_exist"))
check("a plan that never names its slug is found", has("slug", "checkout-retry"))
check("findings carry a line number",
      all(isinstance(f["line"], int) and f["line"] >= 1 for f in bad))

# Creating a file that is already there is the mirror-image mistake and is just
# as wrong: it means the plan was written against a stale view of the tree.
created = az.analyze(GOOD.replace("- Modify: `src/checkout.ts:submit`",
                                  "- Create: `src/checkout.ts`"),
                     exists=exists_good, slug="checkout-retry")
check("a Create target that already exists is found",
      any(f["code"] == "path" and "already exists" in f["finding"] for f in created),
      str(created))

# An exception is legal -- that is the point of tick-or-justify. It must not be
# reported as a finding, or the rule collapses back into a prohibition.
justified = BAD + "\n## Complexity tracking\nI: this plan predates the evidence rule.\n"
check("an unticked article WITH a justification is not a finding",
      not any(f["code"] == "constitution" and "complexity" in f["finding"].lower()
              for f in az.analyze(justified, exists=lambda p: False)))

check("no plan at all is not an error",
      az.plan_text(ROOT, "no-such-slug-anywhere") == (None, ""))

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All analyze tests passed")

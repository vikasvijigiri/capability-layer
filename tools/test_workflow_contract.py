#!/usr/bin/env python3
"""Every `.claude/workflows/*.js` matches the contract that makes it invocable.

A workflow that does not match the contract is not a broken workflow -- it is an
absent one. It never appears as a command, never shows in `/workflows`, and gets
none of the runtime's concurrency caps or resume caching. Nothing errors.

That is not hypothetical here. `decisions/2026-08-07-one-workflow-engine.md`
deleted a 101-line `feature-delivery.js` for four reasons, and the first was
exactly this: it exported `run({ args, agent, pipeline })` instead of top-level
code, so `/feature-delivery` never existed. The file was present, plausible, and
unreachable for its whole life. Its test suite was 47 lines whose substantive
assertion was `text.count("agent(") < 5` -- reason four.

So this asserts the shape, and the two design rules the ADR turned into policy:

  - **One budget table.** `_hooklib.FAILURE_BUDGETS` and `loop.py`'s ladders are
    the only place attempt counts live. A workflow restating them gets a
    `deterministic` failure the right number of attempts by coincidence, which is
    what happened last time and what nothing asserted.
  - **No durable state in a workflow.** Run state died with the process before.
    That is acceptable only because nothing here IS durable state -- the plan's
    checkboxes and git are the record. A workflow that writes state is claiming
    otherwise.

Run: python tools/test_workflow_contract.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".claude" / "workflows"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


# Runtime globals a workflow may use. Anything outside this that looks like an
# import or a Node API is a script that will fail at run time, not author time.
RUNTIME_GLOBALS = {"agent", "parallel", "pipeline", "phase", "log", "args",
                   "budget", "workflow"}

# Forbidden because the runtime does not provide them. `Date.now` and
# `Math.random` specifically BREAK RESUME -- a cached prefix would replay with
# different values -- and the runtime throws on them rather than tolerating it.
FORBIDDEN_APIS = (
    (re.compile(r"\brequire\s*\("), "require() -- no module system in a workflow"),
    (re.compile(r"(?m)^\s*import\s+.*\bfrom\b"), "import -- no module system"),
    (re.compile(r"\bfs\.\w"), "fs -- no filesystem access"),
    (re.compile(r"\bchild_process\b"), "child_process -- no subprocess"),
    (re.compile(r"\bprocess\.(env|argv|cwd)"), "process.* -- no Node globals"),
    (re.compile(r"\bDate\.now\s*\("), "Date.now() -- throws; it breaks resume"),
    (re.compile(r"\bMath\.random\s*\("), "Math.random() -- throws; it breaks resume"),
    (re.compile(r"\bnew\s+Date\s*\(\s*\)"), "argless new Date() -- throws"),
)

# The budget vocabulary that must not be restated in JavaScript.
BUDGET_WORDS = re.compile(
    r"\b(BUDGETS?|MAX_ATTEMPTS|FAILURE_BUDGETS|max_attempts)\b")

scripts = sorted(WORKFLOWS.glob("*.js")) if WORKFLOWS.is_dir() else []

if not WORKFLOWS.is_dir():
    print("NOTE: no .claude/workflows/ directory -- nothing to check, and that is "
          "a valid state. The policy engine (resume.py + loop.py) is the spine; a "
          "workflow is an optimisation for a bounded fan-out.")
    print("\nAll workflow-contract tests passed")
    sys.exit(0)

check("a workflows directory with no scripts is not left behind",
      bool(scripts) or not any(WORKFLOWS.iterdir()),
      "an empty .claude/workflows/ reads as a capability that exists and does "
      "nothing")

for path in scripts:
    text = path.read_text(encoding="utf-8", errors="replace")
    name = path.name

    # --- 1. the shape that makes it invocable -------------------------------
    check(f"{name} exports a meta block",
          re.search(r"(?m)^export\s+const\s+meta\s*=\s*\{", text) is not None,
          "without `export const meta = {...}` the runtime cannot list or "
          "invoke it, and nothing errors")
    check(f"{name} does NOT export a run() wrapper",
          re.search(r"export\s+(default\s+)?(async\s+)?function\s+run\b", text)
          is None
          and re.search(r"export\s+default\s+", text) is None,
          "this is the exact shape that made feature-delivery.js unreachable: "
          "the contract is top-level code, not an exported entry point")

    meta_match = re.search(r"(?m)^export\s+const\s+meta\s*=\s*\{(.*?)^\}",
                           text, re.S)
    if meta_match:
        meta = meta_match.group(1)
        check(f"{name} meta declares a name", "name:" in meta)
        check(f"{name} meta declares a description", "description:" in meta)
        check(f"{name} meta declares phases", "phases:" in meta)
        # A pure literal. A computed meta cannot be read without executing the
        # script, so the runtime requires it to be static.
        check(f"{name} meta is a pure literal",
              not re.search(r"\$\{|\.\.\.|\w+\(", meta),
              "no template interpolation, spreads or calls -- the runtime reads "
              "this without running the script")

        # Every phase() call should have a matching meta entry, or its progress
        # lands in an unnamed group.
        declared = set(re.findall(r"title:\s*'([^']+)'", meta)) | \
            set(re.findall(r'title:\s*"([^"]+)"', meta))
        used = set(re.findall(r"phase\(\s*'([^']+)'\s*\)", text)) | \
            set(re.findall(r'phase\(\s*"([^"]+)"\s*\)', text))
        # Dynamic phase labels are legitimate; only literal ones are checkable.
        unknown = sorted(used - declared)
        check(f"{name} every literal phase() has a meta entry", not unknown,
              f"undeclared: {unknown}")

    # --- 2. it actually uses the runtime ------------------------------------
    check(f"{name} dispatches at least one agent",
          re.search(r"\bagent\s*\(", text) is not None,
          "a workflow that spawns nothing is a script, and a script belongs in "
          "tools/ where it can be tested directly")

    # --- 3. no forbidden API ------------------------------------------------
    for pattern, why in FORBIDDEN_APIS:
        hit = pattern.search(text)
        check(f"{name} avoids {why.split(' -- ')[0]}", hit is None,
              f"{why}; found {hit.group(0)!r}" if hit else "")

    # --- 4. one budget table, and it is not here ----------------------------
    #
    # Comments are stripped first: this file's own reasoning NAMES the forbidden
    # identifiers in order to forbid them, and a check that cannot tell an
    # explanation from a declaration fails on its own documentation.
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    code = re.sub(r"(?m)^\s*//.*$", "", code)
    budget_hit = BUDGET_WORDS.search(code)
    check(f"{name} does not restate a budget table", budget_hit is None,
          f"found {budget_hit.group(0)!r} -- attempt counts live in "
          f"_hooklib.FAILURE_BUDGETS and tools/loop.py, and a second copy got "
          f"the last workflow deleted" if budget_hit else "")

    # --- 5. it reports rather than decides ----------------------------------
    check(f"{name} returns something for the caller to act on",
          re.search(r"(?m)^return\s", text) is not None,
          "a workflow that returns nothing has made a decision the policy engine "
          "should have made")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All workflow-contract tests passed ({len(scripts)} script(s))")

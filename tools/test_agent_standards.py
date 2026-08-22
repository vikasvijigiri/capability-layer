#!/usr/bin/env python3
"""Validate agent safety and portability invariants beyond basic routing.

Task 4 (docs/plans/2026-08-10-checklist-completion.md) adds one more: every
agent whose `tools:` line grants `Write` or `Edit` must declare
`allowed-paths:` in its own frontmatter, because
`.claude/hooks/pre-edit/02-agent-scope-guard.py` is the mechanism that reads
that field and denies a write outside it. A read-only agent has nothing to
enforce and must NOT be forced to declare one -- asserting it on all eight
would make the check noise on the six that never touch a file.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude" / "agents"
GUARD = ROOT / ".claude" / "hooks" / "pre-edit" / "02-agent-scope-guard.py"
# `researcher` merged the former `repo-cartographer` (read-only) with
# `researcher` (Write, scoped to docs/research/digests/** via
# allowed-paths) on 2026-08-21 -- the merged agent declares Write, so it is
# correctly absent here, same as `implementer` (merged `implementer`).
READ_ONLY = {
    "Explore", "reviewer", "debugger", "architect", "tester",
    "security-reviewer",
}
# Hook runtime is a correctness property here (CLAUDE.md: one hook shipped at
# 5.2s/turn because nothing measured it). This is generous headroom for a
# cold Python interpreter start on Windows, not a target to approach.
MAX_HOOK_SECONDS = 3.0

failures: list[str] = []

for path in sorted(AGENTS.glob("*.md")):
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        failures.append(f"{path.name}: missing frontmatter")
        continue
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    name = fields.get("name", path.stem)
    tools = fields.get("tools", "")
    description = fields.get("description", "")
    if not fields.get("tools"):
        failures.append(f"{name}: missing explicit tools allowlist")
    if "mcp__" in tools:
        failures.append(f"{name}: harness-specific MCP tool in allowlist")
    if len(description) > 500:
        failures.append(f"{name}: description exceeds 500 characters")
    if "Do NOT use" not in description:
        failures.append(f"{name}: description lacks a Do NOT use boundary")
    if name in READ_ONLY and re.search(r"\b(Write|Edit)\b", tools):
        failures.append(f"{name}: read-only agent has a write tool")
    writes = bool(re.search(r"\b(Write|Edit)\b", tools))
    if writes and not fields.get("allowed-paths"):
        failures.append(
            f"{name}: grants Write/Edit but declares no allowed-paths -- "
            f"02-agent-scope-guard.py has nothing to enforce"
        )
    if not writes and fields.get("allowed-paths"):
        failures.append(
            f"{name}: declares allowed-paths but has no Write/Edit tool -- "
            f"noise, not a scope"
        )

if failures:
    for failure in failures:
        print(f"FAIL: {failure}")
    raise SystemExit(1)

print(f"OK: {len(list(AGENTS.glob('*.md')))} agents satisfy safety and portability invariants")


# --- fire the guard for real ------------------------------------------------
#
# CLAUDE.md: "A hook bug's symptom is silence." A diff proves what was
# intended, not what runs, so this fires 02-agent-scope-guard.py through the
# exact entry points a real dispatch and a human check use: `HOOK_PAYLOAD`
# plus environment (matching Claude Code's own contract, see _hooklib.py),
# invoked as a subprocess so `sys.path`/import side effects cannot leak
# between cases.

def fire_guard(payload: dict, env_extra: dict) -> tuple[str, float]:
    env = os.environ.copy()
    env.update(env_extra)
    env["HOOK_PAYLOAD"] = json.dumps(payload)
    env["PYTHONIOENCODING"] = "utf-8"
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        env=env, capture_output=True, text=True, timeout=10,
    )
    elapsed = time.perf_counter() - start
    return proc.stdout.strip(), elapsed

IN_SCOPE_PATH = str(ROOT / "docs" / "research" / "digests" / "example.md")
OUT_OF_SCOPE_PATH = str(ROOT / "CLAUDE.md")

# 1. No dispatched agent (the main session) -- must stay silent regardless of
#    path, because there is no declared scope for the interactive session.
out, elapsed = fire_guard(
    {"tool_name": "Write", "tool_input": {"file_path": OUT_OF_SCOPE_PATH}}, {})
if out:
    failures.append(f"guard fired with no UAIOS_AGENT_NAME set: {out!r}")
if elapsed > MAX_HOOK_SECONDS:
    failures.append(f"guard (no agent) took {elapsed:.2f}s > {MAX_HOOK_SECONDS}s")

# 2. A dispatched, statically-scoped agent (researcher) writing inside its
#    declared scope -- silent.
out, elapsed = fire_guard(
    {"tool_name": "Write", "tool_input": {"file_path": IN_SCOPE_PATH}},
    {"UAIOS_AGENT_NAME": "researcher"},
)
if out:
    failures.append(f"guard denied an in-scope researcher write: {out!r}")
if elapsed > MAX_HOOK_SECONDS:
    failures.append(f"guard (in-scope) took {elapsed:.2f}s > {MAX_HOOK_SECONDS}s")

# 3. The same agent writing OUTSIDE its declared scope -- denied.
out, elapsed = fire_guard(
    {"tool_name": "Write", "tool_input": {"file_path": OUT_OF_SCOPE_PATH}},
    {"UAIOS_AGENT_NAME": "researcher"},
)
try:
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
except Exception:
    decision = None
if decision != "deny":
    failures.append(f"guard did not deny an out-of-scope researcher write: {out!r}")
if elapsed > MAX_HOOK_SECONDS:
    failures.append(f"guard (out-of-scope) took {elapsed:.2f}s > {MAX_HOOK_SECONDS}s")

# 4. A dispatched agent with a `dispatched` (per-round) scope and no
#    UAIOS_AGENT_SCOPE set -- the scope cannot be established, so it must
#    deny rather than allow.
out, elapsed = fire_guard(
    {"tool_name": "Write", "tool_input": {"file_path": OUT_OF_SCOPE_PATH}},
    {"UAIOS_AGENT_NAME": "implementer"},
)
try:
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
except Exception:
    decision = None
if decision != "deny":
    failures.append(
        f"guard allowed implementer with no UAIOS_AGENT_SCOPE set: {out!r}"
    )

# 5. Same agent, with UAIOS_AGENT_SCOPE naming the round's declared files --
#    an in-scope write is silent and an out-of-scope one is still denied.
out, elapsed = fire_guard(
    {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / "tools" / "budget.py")}},
    {"UAIOS_AGENT_NAME": "implementer", "UAIOS_AGENT_SCOPE": "tools/budget.py,tools/test_budget.py"},
)
if out:
    failures.append(f"guard denied implementer inside its dispatched scope: {out!r}")

out, elapsed = fire_guard(
    {"tool_name": "Edit", "tool_input": {"file_path": OUT_OF_SCOPE_PATH}},
    {"UAIOS_AGENT_NAME": "implementer", "UAIOS_AGENT_SCOPE": "tools/budget.py,tools/test_budget.py"},
)
try:
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
except Exception:
    decision = None
if decision != "deny":
    failures.append(
        f"guard allowed implementer outside its dispatched scope: {out!r}"
    )

# --- the claim may not outlive the wiring ------------------------------------
#
# Everything above proves the guard works WHEN `UAIOS_AGENT_NAME` is set. On
# this host nothing sets it: Claude Code spawns subagents itself and runs no
# hook inside one, so on a real dispatch the guard runs and is silent. Audited
# 2026-08-16, where `workflow.md` still listed agent file scope among six
# shipped rails with no precondition -- a reader of the contract got the
# stronger statement, which is the failure mode this layer is least able to see,
# because a dormant control and a working one look identical from outside.
#
# So the dormancy is asserted, in the file that makes the claim. If the wiring
# ever arrives, this fails and the sentence gets rewritten in the same change.

WORKFLOW = ROOT / ".claude" / "workflow.md"
_workflow_text = WORKFLOW.read_text(encoding="utf-8", errors="replace")

_rail_row = next((ln for ln in _workflow_text.splitlines()
                  if "**Agent file scope**" in ln), "")
if not _rail_row:
    failures.append("workflow.md no longer has an Agent file scope rail row")
elif "UAIOS_AGENT_NAME" not in _rail_row:
    failures.append(
        "workflow.md's Agent file scope rail claims enforcement without naming "
        "`UAIOS_AGENT_NAME`, the variable no dispatcher on this host sets")

if "dormant on this host" not in _workflow_text:
    failures.append(
        "workflow.md dropped the dormancy note for agent file scope -- the "
        "guard is silent on this host and the contract must say so")

# Looks for the variable being SET, not merely named -- `env["UAIOS_AGENT_NAME"]
# = ...` or a `{"UAIOS_AGENT_NAME": ...}` literal. A prose mention is how the
# dormancy gets documented, so matching those would make this check fire on its
# own explanation, which it did on the first run.
_SETS_AGENT_NAME = re.compile(r"""UAIOS_AGENT_NAME["']?\s*[:=]""")
_env_setters = [
    path for path in ROOT.rglob("*.py")
    if "node_modules" not in path.parts and "build" not in path.parts
    and path.name not in ("test_agent_standards.py", "02-agent-scope-guard.py")
    and _SETS_AGENT_NAME.search(path.read_text(encoding="utf-8", errors="replace"))
]
if _env_setters:
    failures.append(
        "something now SETS UAIOS_AGENT_NAME outside the guard and this suite "
        f"({[p.name for p in _env_setters]}) -- agent file scope may no longer "
        "be dormant, so the note in workflow.md must be rewritten")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}")
    raise SystemExit(1)

print("OK: 02-agent-scope-guard.py denies out-of-scope writes and stays silent in-scope")
print("OK: the file-scope claim names its precondition and is marked dormant")

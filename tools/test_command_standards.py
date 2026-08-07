#!/usr/bin/env python3
"""Validate slash-command contracts, safety boundaries, and live references."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ROOT / ".claude" / "commands"
failures: list[str] = []

for path in sorted(COMMANDS.glob("*.md")):
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        failures.append(f"{path.name}: missing frontmatter")
        continue
    front = match.group(1)
    description = re.search(r"^description:\s*(.+)$", front, re.M)
    if not description or not description.group(1).strip():
        failures.append(f"{path.name}: missing description")
    if not re.search(r"^Mode:\s*(read-only|mutating)$", text, re.M):
        failures.append(f"{path.name}: missing Mode contract")
    if "$ARGUMENTS" not in text:
        failures.append(f"{path.name}: missing $ARGUMENTS handling")
    if "python tools/" in text:
        for rel in re.findall(r"python (tools/[A-Za-z0-9_.\\/-]+\.py)", text):
            if not (ROOT / rel).is_file():
                failures.append(f"{path.name}: references missing {rel}")

save = (COMMANDS / "save.md").read_text(encoding="utf-8")
for phrase in ("AskUserQuestion", "Never push", "/verify"):
    if phrase not in save:
        failures.append(f"save.md: missing safety contract {phrase!r}")

# --- every mutating command asks with the tool, not in prose ------------------
#
# "Ask for explicit confirmation" is a sentence the model can satisfy by writing
# a question into its reply, which the user can answer with silence and which
# scrolls out of view in a long turn. `AskUserQuestion` renders a decision the
# user clicks, so approval is a recorded event rather than something inferred
# from whatever they said next. Asserted here because a command that mutates
# state is exactly where that distinction is load-bearing.
#
# read-only commands are exempt by construction: they have nothing to confirm.
for path in sorted(COMMANDS.glob("*.md")):
    text = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"^Mode:\s*mutating$", text, re.M) and "AskUserQuestion" not in text:
        failures.append(f"{path.name}: mutating but never names AskUserQuestion — "
                        f"a prose confirmation is answerable by silence")

verify = (COMMANDS / "verify.md").read_text(encoding="utf-8")
if "tools/run_checks.py --tier all --require-test" not in verify:
    failures.append("verify.md: does not call the canonical full check runner")
if "six test suites" in verify.lower():
    failures.append("verify.md: contains stale six-suite inventory")

for path in sorted(COMMANDS.glob("*.md")):
    if "install-layer" in path.read_text(encoding="utf-8", errors="replace"):
        failures.append(f"{path.name}: references removed install-layer command")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}")
    raise SystemExit(1)

print(f"OK: {len(list(COMMANDS.glob('*.md')))} command contracts validated")

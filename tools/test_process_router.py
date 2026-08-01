#!/usr/bin/env python3
"""Tests for process-skill routing: matching, fail-open, and heading validity.

`.claude/routing/process-skills.md` names skills directly rather than a prefix,
which makes a wrong heading a lie the router will repeat every turn -- it would
tell the model to invoke a skill that does not exist. `capabilities.md` cannot
have that failure mode (a bad prefix simply matches nothing), so it is asserted
here instead of left to review.

Also asserts the two routing files stay disjoint in the sense that matters: an
entry here must not be a `<domain>-` prefixed skill, because those are already
reachable through the capability router and two blocks for one signal is noise.

Run: python tools/test_process_router.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "pre-run" / "05-process-skill-router.py"
ROUTING = ROOT / ".claude" / "routing" / "process-skills.md"
CAPABILITIES = ROOT / ".claude" / "routing" / "capabilities.md"
SKILLS = ROOT / ".claude" / "skills"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def run_hook(prompt: str) -> str:
    """Injected additionalContext for a prompt, or '' when the hook stays silent."""
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True, text=True, encoding="utf-8",
    )
    if p.returncode != 0:
        return f"<hook exited {p.returncode}: {p.stderr.strip()}>"
    out = p.stdout.strip()
    if not out:
        return ""
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --- 1. matching behaviour -------------------------------------------------

for prompt, expected in [
    # The prompt this hook exists because of: it matches the `research`
    # capability on "papers", and nothing named `brainstormer`.
    ("Lets brainstorm about collecting pioneering papers in a physics field",
     "brainstormer"),
    ("any ideas for how to structure this?", "brainstormer"),
    ("can you review this before I ship it", "code-review"),
    ("what stack should we use for this", "stack-selector"),
    ("it broke again, same error as before", "error-recovery"),
    ("where did we get to yesterday", "knowledge-manager"),
    ("what will this break if I change it", "impact-analysis"),
]:
    ctx = run_hook(prompt)
    check(f"matches {expected!r} for {prompt[:40]!r}", f"`{expected}`" in ctx,
          f"got: {ctx[:160]!r}")

# Word-boundary matching: substrings must not fire. This is the exact bug class
# that regressed in hook 02 -- `retro` inside "retrograde", `prd` inside a word.
for prompt in [
    "the retrograde motion of mercury",
    "hello there",
    "deploy this to production",   # capability territory, not process
]:
    check(f"stays silent for {prompt!r}", run_hook(prompt) == "",
          f"got: {run_hook(prompt)[:120]!r}")

# Plural tolerance on the final word, same rule as hook 02.
check("plural tolerance ('bounce ideas' matches as written)",
      "`brainstormer`" in run_hook("lets bounce ideas around"))

# The injected block is a recurring per-turn cost, so its size is asserted, not
# left to drift. A one-skill match must stay under 40 tokens (~160 chars).
_block = run_hook("lets brainstorm this")
check("injected block stays small", len(_block) < 160,
      f"{len(_block)} chars (~{len(_block)//4} tokens)")

# --- 2. fail-open ----------------------------------------------------------

backup = ROUTING.read_text(encoding="utf-8")
try:
    ROUTING.unlink()
    check("fails open when routing file is missing",
          run_hook("lets brainstorm this") == "")
finally:
    ROUTING.write_text(backup, encoding="utf-8")

# Malformed input must not crash the turn.
p = subprocess.run([sys.executable, str(HOOK)], input="not json at all",
                   capture_output=True, text=True, encoding="utf-8")
check("fails open on malformed payload", p.returncode == 0,
      f"exit {p.returncode}: {p.stderr.strip()[:120]}")

# --- 3. every heading names a real, unprefixed skill -----------------------

router = load_module(HOOK, "process_skill_router")
entries = router.load_process_skills()
check("routing file parses to at least 20 entries", len(entries) >= 20,
      f"got {len(entries)}")

skill_dirs = {p.name for p in SKILLS.iterdir() if p.is_dir()}
for skill, words in entries:
    check(f"{skill} is a real skill directory", skill in skill_dirs)
    check(f"{skill} has keywords", bool(words))

# --- 4. no overlap with the capability router ------------------------------

domains = [
    m.group(1).strip().lower()
    for m in re.finditer(r"^## +(\S+)\s*$", CAPABILITIES.read_text(encoding="utf-8"), re.M)
]
for skill, _ in entries:
    check(f"{skill} is not already covered by a capability prefix",
          not any(skill.startswith(f"{d}-") for d in domains))

# `task-intake` has its own dedicated hook (03); a second nudge is noise.
check("task-intake is not duplicated here",
      "task-intake" not in {s for s, _ in entries})

# --- 5. no unrouted process skill goes unnoticed ---------------------------
# Not a hard failure -- a skill may legitimately have no distinctive trigger
# vocabulary -- but an unrouted skill is invisible on a truncated listing turn,
# so it is reported rather than silently accepted.

process_skills = {
    s for s in skill_dirs
    if not any(s.startswith(f"{d}-") for d in domains)
}
routed = {s for s, _ in entries} | {"task-intake"}
unrouted = sorted(process_skills - routed)
if unrouted:
    print(f"NOTE: {len(unrouted)} process skill(s) with no keyword entry: "
          f"{', '.join(unrouted)}")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All process-router tests passed ({len(entries)} entries routed)")

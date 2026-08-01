#!/usr/bin/env python3
"""Tests for skill routing: matching, fail-open, and heading validity.

`.claude/routing/process-skills.md` names skills directly, which makes a wrong
heading a lie the router repeats every turn -- it would tell the model to invoke
a skill that does not exist. That is asserted here rather than left to review.

The capability router and its nine-domain `capabilities.md` were deleted on
2026-08-01 along with the 85 skills they routed to; the overlap assertions that
used to live here went with them, since there is no longer a second router to
overlap with.

Run: python tools/test_process_router.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "pre-run" / "05-process-skill-router.py"
ROUTING = ROOT / ".claude" / "routing" / "process-skills.md"
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
    # The prompt this hook exists because of: it used to match the `research`
    # capability on "papers", and nothing named `brainstormer`.
    ("Lets brainstorm about collecting pioneering papers in a physics field",
     "brainstormer"),
    ("any ideas for how to structure this?", "brainstormer"),
    ("what are our options here", "brainstormer"),
    ("write the implementation plan for this spec", "writing-plans"),
    ("turn the spec into tasks", "writing-plans"),
    ("break this into bite-sized tasks", "writing-plans"),
]:
    ctx = run_hook(prompt)
    check(f"matches {expected!r} for {prompt[:40]!r}", f"`{expected}`" in ctx,
          f"got: {ctx[:160]!r}")

# Word-boundary matching: substrings must not fire. This is the exact bug class
# that regressed in the deleted hook 02 -- `retro` inside "retrograde".
for prompt in [
    "the retrograde motion of mercury",
    "hello there",
    "deploy this to production",
]:
    check(f"stays silent for {prompt!r}", run_hook(prompt) == "",
          f"got: {run_hook(prompt)[:120]!r}")

# Plural tolerance on the final word.
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

# --- 3. every heading names a real skill, and every skill is routed --------

router = load_module(HOOK, "process_skill_router")
entries = router.load_process_skills()
check("routing file parses to at least one entry", len(entries) >= 1,
      f"got {len(entries)}")

skill_dirs = {p.name for p in SKILLS.iterdir() if p.is_dir()}
for skill, words in entries:
    check(f"{skill} is a real skill directory", skill in skill_dirs)
    check(f"{skill} has keywords", bool(words))

# The inverse direction. With the capability router gone this file is the only
# routing signal there is, so an unrouted skill is invisible on any turn its
# description is truncated out of the listing. That used to be a NOTE tolerated
# across 86 skills; at this size there is no excuse for it.
unrouted = sorted(skill_dirs - {s for s, _ in entries})
check("every skill has a routing entry", not unrouted,
      f"unrouted: {', '.join(unrouted)}")

# --- 4. frontmatter actually yields a description --------------------------
#
# Routing is only half the trigger surface; `description:` is the other half.
# A description containing ": " followed by a quote makes YAML parse the scalar
# as a mapping, and the description silently vanishes -- the skill still lists,
# still routes, and is untriggerable by description. That happened on
# 2026-08-01 while rewriting these three, and nothing caught it but the skill
# listing rendering the bare title.
#
# Two size limits, deliberately different in kind. 1024 chars of frontmatter is
# the hard spec limit (agentskills.io) and a real failure -- it is asserted.
# 500 chars of description is superpowers' "keep under if possible" guidance
# about listing-truncation budget; richer trigger coverage is worth spending
# some of it, so going over prints a NOTE and does not fail the suite.

HARD_FRONTMATTER = 1024
SOFT_DESC = 500
for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
    text = (d / "SKILL.md").read_text(encoding="utf-8")
    try:
        import yaml  # noqa: PLC0415 - optional dep, only needed for this block
        front = yaml.safe_load(text.split("---", 2)[1])
    except ImportError:
        print("NOTE: pyyaml missing -- frontmatter checks skipped, not passed")
        break
    except Exception as exc:  # noqa: BLE001 - any parse failure is the finding
        check(f"{d.name} frontmatter parses", False, str(exc)[:80])
        continue
    check(f"{d.name} frontmatter parses to a mapping", isinstance(front, dict))
    if not isinstance(front, dict):
        continue
    desc = front.get("description")
    check(f"{d.name} has a non-empty description", bool(desc))
    check(f"{d.name} name matches directory", front.get("name") == d.name,
          f"name={front.get('name')!r}")
    raw = text.split("---", 2)[1]
    check(f"{d.name} frontmatter <= {HARD_FRONTMATTER} chars",
          len(raw) + 8 <= HARD_FRONTMATTER, f"{len(raw) + 8} chars")
    if isinstance(desc, str) and len(desc) > SOFT_DESC:
        print(f"NOTE: {d.name} description is {len(desc)} chars "
              f"(over the {SOFT_DESC} soft target, under the hard limit)")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All process-router tests passed ({len(entries)} entries routed)")

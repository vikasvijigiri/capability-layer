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
import re
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
    # Both asserts are real, not type-checker appeasement: a mistyped path makes
    # spec_from_file_location return None, and the failure surfaces three lines
    # later as `NoneType has no attribute loader` -- which reads like a bug in
    # the module under test rather than a wrong path in this file.
    assert spec is not None, f"no import spec for {path}"
    assert spec.loader is not None, f"no loader for {path}"
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
    # Stage 8 arrived 2026-08-02. This prompt was a *negative* control until
    # then -- it was the plausible ops phrase that correctly matched nothing,
    # because no skill owned the act. Now one does, so it is a positive.
    ("deploy this to production", "releasing"),
    ("roll it back, the smoke check is red", "releasing"),
]:
    ctx = run_hook(prompt)
    check(f"matches {expected!r} for {prompt[:40]!r}", f"`{expected}`" in ctx,
          f"got: {ctx[:160]!r}")

# Word-boundary matching: substrings must not fire. This is the exact bug class
# that regressed in the deleted hook 02 -- `retro` inside "retrograde".
for prompt in [
    "the retrograde motion of mercury",
    "hello there",
    # `deploy` inside `redeployment`, same bug class as `retro`/`retrograde`.
    "the redeployment paperwork is filed",
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

# --- The chain resolves ---------------------------------------------------
#
# This repo's most-repeated failure is a name in prose that resolves to
# nothing: 22 dead references were cleared by hand at 1443ba2, and six hooks
# once shipped naming deleted skills past a green suite. Until now nothing
# asserted that a skill named by another skill exists.
#
# Two properties, both mechanical:
#   1. Every skill named in backticks inside a SKILL.md is a real skill.
#   2. Every skill on the main chain states its successor imperatively, in a
#      `## Next step` section -- not only as a descriptive Routing footnote.
#      A handoff that lives in a footnote is one the reader may treat as
#      commentary, which is exactly how the chain silently stops.

skill_names = {d.name for d in sorted(SKILLS.iterdir()) if d.is_dir()}

# A skill may legitimately name a subagent. Both are resolvable names; neither
# is a dead reference. Discovered from the filesystem here so the resolution
# check below can accept either, with the agents' own frontmatter asserted
# further down.
AGENTS_DIR = ROOT / ".claude" / "agents"
agent_files = {f.stem for f in AGENTS_DIR.glob("*.md")} if AGENTS_DIR.exists() else set()
resolvable = skill_names | agent_files

# Names that look like skills in backticks but are something else here:
# hook event directories, slash commands, and Claude Code agent types. An
# agent type (`general-purpose`) is dispatched through the Agent tool and has
# no .claude/skills/ directory -- naming one is correct, not a dead reference.
NOT_SKILLS = {
    # hook event directories
    "pre-commit", "pre-run", "post-run", "pre-edit", "pre-deploy",
    "session-start", "post-tool", "on-error",
    # slash commands
    "skills-doctor",
    # Claude Code agent types
    "general-purpose", "statusline-setup",
    # document sections and prose
    "task-brief-style", "session-context",
    # code-review angles handed to a diff-reviewer, not names of anything
    "test-quality",
}

CHAIN_SUCCESSOR = {
    "brainstormer": "writing-plans",
    "writing-plans": "executing-plans",
    "executing-plans": "verifying-work",
    # no-slop sweeps the repo BEFORE review, so its repairs land inside the
    # diff code-review reads. After review they would ship unreviewed.
    "verifying-work": "no-slop",
    "no-slop": "code-review",
    "code-review": "delivering",
    # delivering branches: `releasing` when the repo has a deploy target,
    # `knowledge-manager` directly when it has none. The chain successor is the
    # one that continues the line; the other is the skip.
    "delivering": "releasing",
    "releasing": "knowledge-manager",
}

for d in sorted(SKILLS.iterdir()):
    if not d.is_dir():
        continue
    skill_md = d / "SKILL.md"
    if not skill_md.exists():
        continue
    text = skill_md.read_text(encoding="utf-8")
    body = text.split("---", 2)[-1]  # skip frontmatter; it names peers freely

    for name in sorted(set(re.findall(r"`([a-z][a-z0-9]+(?:-[a-z0-9]+)+)`", body))):
        if name in NOT_SKILLS or name.endswith(".py") or name.endswith(".md"):
            continue
        if "/" in name or "." in name:
            continue
        check(f"{d.name} names a real skill or agent: `{name}`",
              name in resolvable,
              f"neither .claude/skills/{name}/ nor .claude/agents/{name}.md")

    successor = CHAIN_SUCCESSOR.get(d.name)
    if successor:
        check(f"{d.name} has a '## Next step' section", "## Next step" in body)
        nxt = body.split("## Next step", 1)[-1].split("## ", 1)[0] if "## Next step" in body else ""
        check(f"{d.name} names `{successor}` as its next step",
              f"`{successor}`" in nxt)

# task-brief branches three ways, so it is checked for the section only.
tb = (SKILLS / "task-brief" / "SKILL.md").read_text(encoding="utf-8")
check("task-brief has a '## Next step' section", "## Next step" in tb)

# The `## Next step` section and the `## Routing` terminal-handoff line are two
# statements of the same fact, so they can disagree -- and three of them did on
# 2026-08-02, each written before the successor skill existed. Assert they name
# the same skill.
for skill, successor in CHAIN_SUCCESSOR.items():
    body = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    routing = body.split("## Routing", 1)[-1] if "## Routing" in body else ""
    # Read the WHOLE bullet, not its first line: these bullets wrap, and the
    # successor often lands on the continuation line. A first-line-only check
    # reported writing-plans as disagreeing with itself.
    handoff = ""
    lines = routing.splitlines()
    for i, line in enumerate(lines):
        if "Terminal handoff" not in line:
            continue
        bullet = [line]
        for cont in lines[i + 1:]:
            if cont.strip().startswith("- ") or cont.startswith("#") or not cont.strip():
                break
            bullet.append(cont)
        handoff = " ".join(bullet)
        break
    check(f"{skill} Routing states a terminal handoff", bool(handoff))
    if handoff:
        check(f"{skill} Routing agrees with its Next step (`{successor}`)",
              f"`{successor}`" in handoff,
              f"Routing says: {handoff.strip()[:70]}")

# --- workflow.md agrees with itself and with the skills --------------------
#
# The defect this catches was found by reading, not by any check: the chain
# table listed Document (10) before Self-review (11) and Deliver (12), while
# the handoff graph five sections below put knowledge-manager last. Two
# statements of one ordering in one file, disagreeing, both plausible.
#
# Three assertions: the table's skills are real, the linear stages appear in the
# same order as the handoff chain, and each skill's own "Workflow stage N" line
# matches the number the table gives it.

WORKFLOW = ROOT / ".claude" / "workflow.md"
wf = WORKFLOW.read_text(encoding="utf-8")

# Rows look like: | 4 | Execute | `executing-plans` | ... | ... |
table = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*`([a-z-]+)`", wf, re.M)
check("workflow.md chain table parses", len(table) >= 8, f"got {len(table)} rows")

stage_of = {skill: int(num) for num, _name, skill in table}
for skill in stage_of:
    check(f"workflow.md stage owner `{skill}` is a real skill",
          skill in skill_names)

numbers = [int(n) for n, _, _ in table]
check("workflow.md stage numbers are 1..N with no gaps or repeats",
      numbers == list(range(1, len(numbers) + 1)), f"got {numbers}")

# The linear chain in the table must be the same order the skills hand off in.
linear = [skill for _n, _name, skill in table]
walk, cur = [], linear[0]
while cur:
    walk.append(cur)
    cur = CHAIN_SUCCESSOR.get(cur)
# task-brief branches, so the walk starts at its most common successor instead.
expected_tail = linear[1:]
check("handoff chain visits the table's stages in table order",
      walk[1:] == expected_tail[:len(walk) - 1] or walk == expected_tail,
      f"table={linear}  walk={walk}")

# Each skill states its own stage number, and it must be the table's number.
for skill, num in stage_of.items():
    body = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"Workflow stage (\d+)", body)
    if not m:
        continue  # only the stages that claim a number are asserted
    check(f"{skill} claims the stage number workflow.md gives it ({num})",
          int(m.group(1)) == num, f"skill says {m.group(1)}, table says {num}")

# --- agents resolve, and are reachable -------------------------------------
#
# Subagents have the same invisibility failure as skills: the lead agent picks
# one by reading its `description`, so a bad name or a missing description makes
# an agent that exists and never runs. And an agent no skill names is an agent
# nobody will ever dispatch -- dead weight that still costs a listing entry.
#
# Tools are asserted as an allowlist because the failure is silent in the other
# direction: an agent with no `tools:` line inherits everything, so a reviewer
# agent quietly gains Write and Edit.

AGENTS = AGENTS_DIR
agent_names: set[str] = set()

if AGENTS.exists():
    for f in sorted(AGENTS.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        try:
            import yaml  # noqa: PLC0415
            front = yaml.safe_load(text.split("---", 2)[1])
        except ImportError:
            front = None
            break
        except Exception as exc:  # noqa: BLE001
            check(f"agent {f.stem} frontmatter parses", False, str(exc)[:80])
            continue
        check(f"agent {f.stem} frontmatter is a mapping", isinstance(front, dict))
        if not isinstance(front, dict):
            continue
        agent_names.add(f.stem)
        check(f"agent {f.stem} name matches filename",
              front.get("name") == f.stem, f"name={front.get('name')!r}")
        desc = front.get("description")
        check(f"agent {f.stem} has a description", bool(desc))
        # The description is the only thing the lead agent reads when deciding
        # whether to delegate, so it must say when NOT to use it too.
        if isinstance(desc, str):
            check(f"agent {f.stem} description says when not to use it",
                  "Do NOT use" in desc or "Do not use" in desc)
        check(f"agent {f.stem} allowlists its tools", bool(front.get("tools")),
              "no tools: line -- inherits every tool, including Write")
        check(f"agent {f.stem} pins a model", bool(front.get("model")))

    check("at least one agent exists", bool(agent_names))

    # Every agent is named by a skill, and every agent a skill names exists.
    named_by_skills: set[str] = set()
    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        body = (d / "SKILL.md").read_text(encoding="utf-8")
        for name in set(re.findall(r"`([a-z][a-z0-9]+(?:-[a-z0-9]+)+)`", body)):
            if name in agent_names:
                named_by_skills.add(name)

    orphans = sorted(agent_names - named_by_skills)
    check("every agent is named by at least one skill", not orphans,
          f"unreachable: {', '.join(orphans)}")

    # ...and the reference points back. An agent runs in a fresh context with its
    # own file as the whole brief: if it does not name its dispatcher, it cannot
    # know where its boundary is. That is not theoretical -- `failure-investigator`
    # must not write `ISSUES.md` and `task-implementer` must not tick the plan's
    # checkboxes, and both facts live only in the sentence naming the owner.
    #
    # Found on 2026-08-03 by a throwaway script: two of four agents were missing
    # it, which is the inconsistency worth failing on either way.
    dispatcher_names = sorted(p.name for p in SKILLS.iterdir() if p.is_dir())
    for f in sorted(AGENTS.glob("*.md")):
        if f.stem not in agent_names:
            continue
        body = f.read_text(encoding="utf-8")
        dispatchers = [
            d for d in dispatcher_names
            if f.stem in (SKILLS / d / "SKILL.md").read_text(encoding="utf-8")
        ]
        if not dispatchers:
            continue  # already reported as an orphan above
        check(f"agent {f.stem} names its dispatcher",
              any(d in body for d in dispatchers),
              f"dispatched by {dispatchers} but names none of them")

# --- routing keywords are unambiguous --------------------------------------
#
# A keyword claimed by two skills makes the router name both on the same turn,
# which is worse than naming neither: the reader has to arbitrate, which is the
# job the router was supposed to do.

seen: dict[str, str] = {}
collisions: list[str] = []
for skill, words in entries:
    for w in words:
        if w in seen and seen[w] != skill:
            collisions.append(f"{w!r} ({seen[w]} + {skill})")
        seen[w] = skill
check("no keyword is claimed by two skills", not collisions,
      "; ".join(collisions))

# A keyword that contains another skill's keyword fires both entries at once.
contained = []
for word, owner in seen.items():
    for other, other_owner in seen.items():
        if word != other and owner != other_owner and other in word:
            contained.append(f"{word!r} ({owner}) contains {other!r} ({other_owner})")
check("no keyword contains another skill's keyword", not contained,
      "; ".join(contained[:4]))

# Keywords must be lowercase: the hook lowercases the prompt but not the file,
# so an uppercase keyword can never match anything.
uppercase = [w for w, _ in seen.items() if w != w.lower()]
check("every keyword is lowercase", not uppercase, ", ".join(uppercase[:5]))

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All process-router tests passed ({len(entries)} entries routed)")

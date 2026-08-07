#!/usr/bin/env python3
"""Tests that the skill and agent layer resolves against itself.

Skills trigger from their own `description:` frontmatter -- there is no keyword
router. The prompt router and `routing/process-skills.md` were deleted on
2026-08-04: a hook whose only output is the name of a skill couples two
independent things and duplicates a routing decision nothing validated. The
matching, fail-open and keyword assertions went with it.

What remains is the part that still has teeth: frontmatter parses and yields a
description, every skill named in prose resolves, the chain's successors are
stated imperatively, workflow.md agrees with itself, and the agents declare their
bounds.

Run: python tools/test_process_router.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)






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

# Every description is injected on every turn, so their sum is a standing cost
# paid before the user types anything. Reported, never enforced: a hard ceiling
# turns each new skill into a hunt for words to cut from unrelated ones, and the
# trigger phrases are the part that would go first -- which is the part that
# makes a skill fire at all. Measured 7813 chars across 22 skills on 2026-08-07
# and tightened to 6721 the same day by deleting framing, not triggers.
DESC_BUDGET: list[int] = []
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
    if isinstance(desc, str):
        DESC_BUDGET.append(len(desc))

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
    "pre-commit", "post-run", "pre-edit", "pre-deploy", "session-start",
    "pre-compact", "on-artifact-create", "global-session-start",
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

# --- successors a skill must NOT hand to ------------------------------------
#
# `CHAIN_SUCCESSOR` asserts the POSITIVE successor and has no `task-brief` entry
# at all, because it branches -- so nothing checked its successors in either
# direction. `task-brief` listed `writing-plans` as a third branch in two places
# while FOUR others said a brief is not a spec: its own step 6, `writing-plans`'
# description ("Do NOT use ... for a six-line brief"), workflow.md's Consumes
# column ("an approved spec"), and workflow.md's diagram, which draws no arrow
# between them. Six statements, two of them wrong, every check green.
#
# A mention is allowed only where it is NEGATED -- the skills here explain what
# they refuse, so a bare ban on the name would be unmaintainable.

FORBIDDEN_SUCCESSOR = {
    "task-brief": ("writing-plans",
                   "stage 3 consumes an approved spec, not a six-line brief"),
}
_NEGATED = re.compile(r"\b(never|not|no|nor)\b", re.I)

# The marker must sit IMMEDIATELY before the name. Sentence-level matching was
# tried first and flagged "which produces the spec `writing-plans` requires" --
# a description of what the skill consumes, not a handoff to it. A rule that
# fires on correct prose gets the check deleted rather than the prose fixed.
_HANDOFF_NEAR = (r"(?:invoke|go to|hand (?:it |this |off )?to|proceed to|"
                 r"→|->|·|\bto)\s*\**`{}`")


def positive_mentions(chunk: str, name: str) -> list[str]:
    """Sentences that hand off to `name` rather than merely mentioning it."""
    near = re.compile(_HANDOFF_NEAR.format(re.escape(name)), re.I)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n(?=\s*[-*\d])", chunk)
            if near.search(s) and not _NEGATED.search(s)]


for _skill, (_bad, _why) in FORBIDDEN_SUCCESSOR.items():
    _body = (SKILLS / _skill / "SKILL.md").read_text(encoding="utf-8")
    for _section in ("## Next step", "## Routing"):
        if _section not in _body:
            continue
        _chunk = _body.split(_section, 1)[1].split("\n## ", 1)[0]
        _bad_lines = positive_mentions(_chunk, _bad)
        check(f"{_skill}'s '{_section}' does not hand off to `{_bad}`",
              not _bad_lines, f"{_why}; found: {_bad_lines[:1]}")

# The same invariant in the file that OWNS the chain. Asserted on the whole
# paragraph, since the branch list wraps across lines.
_wf_text = WORKFLOW.read_text(encoding="utf-8")
_paras = [p for p in _wf_text.split("\n\n") if "task-brief` branches" in p]
check("workflow.md still describes how task-brief branches", bool(_paras))
if _paras:
    check("workflow.md does not branch task-brief to `writing-plans`",
          not positive_mentions(_paras[0], "writing-plans"),
          "the chain owner contradicts both skills' own text")

# Each skill states its own stage number, and it must be the table's number.
for skill, num in stage_of.items():
    body = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"Workflow stage (\d+)", body)
    if not m:
        continue  # only the stages that claim a number are asserted
    check(f"{skill} claims the stage number workflow.md gives it ({num})",
          int(m.group(1)) == num, f"skill says {m.group(1)}, table says {num}")

# Every stage number written in workflow.md's PROSE agrees with the table.
#
# The chain table was right the whole time; four references *around* it drifted
# by one when `no-slop` was inserted at stage 6 on 2026-08-02. The Parallelism
# table said "6 Review" (Review is 7), "the sign-off in stage 6, the approval in
# stage 7" was off by one twice, and "Where state lives" filed `decisions/` under
# 9 (`knowledge-manager` is 10). Nothing caught any of it: the assertions above
# only parse the table and confirm its owners exist, so the table cannot disagree
# with itself -- but it never had to agree with the paragraphs.
#
# This is checkable only because the prose names the owner beside the number.
# A bare "stage 6" is unverifiable, so the convention is `N \`owner\`` or
# `N StageName`, and that convention is what this asserts.
stage_name_of = {name.strip().lower(): int(num) for num, name, _s in table}

prose_refs = []  # (written_number, what, expected_number)
for m in re.finditer(r"(?<!\d)(\d{1,2})\s+`([a-z-]+)`", wf):
    written, name = int(m.group(1)), m.group(2)
    if name in stage_of:
        prose_refs.append((written, f"`{name}`", stage_of[name]))
for m in re.finditer(r"(?<!\d)(\d{1,2})\s+([A-Z][a-z]+)\b", wf):
    written, name = int(m.group(1)), m.group(2).lower()
    if name in stage_name_of:
        prose_refs.append((written, name.title(), stage_name_of[name]))

wrong = [f"{what} written as {written}, table says {expected}"
         for written, what, expected in prose_refs if written != expected]
check(f"every stage number in workflow.md prose matches the table "
      f"({len(prose_refs)} reference(s))", not wrong, "; ".join(wrong[:6]))

# The convention only helps if it is actually used, so a floor on how many
# references are checkable. Rewriting `N \`owner\`` back into a bare "stage N"
# would otherwise silently reduce coverage to zero and still pass.
check("workflow.md prose keeps its stage references checkable",
      len(prose_refs) >= 12, f"only {len(prose_refs)} checkable reference(s)")

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

    # Agents that override a Claude Code BUILT-IN. The harness invokes these by
    # name, so "no skill dispatches it" is not the unreachability bug this check
    # exists to catch -- it is how they are meant to work. They exist only to
    # change the built-in's frontmatter (`Explore` is here to pin `model: haiku`).
    #
    # Narrow on purpose: exempting by name, not by a pattern, so a genuinely
    # orphaned fan-out agent can never slip through by being called something
    # plausible.
    BUILTIN_OVERRIDES = {"Explore"}

    orphans = sorted(agent_names - named_by_skills - BUILTIN_OVERRIDES)
    check("every agent is named by at least one skill", not orphans,
          f"unreachable: {', '.join(orphans)}")

    # The exemption must stay honest: an override has to actually override
    # something, so its filename is its identity and the frontmatter `name:` has
    # to match it exactly. A typo here is a new agent nobody dispatches.
    for name in sorted(BUILTIN_OVERRIDES):
        f = AGENTS / f"{name}.md"
        check(f"built-in override {name} exists and pins a model",
              f.is_file() and re.search(r"^model:\s*\S+", f.read_text(encoding="utf-8"),
                                        re.M) is not None,
              "an override with no model: field changes nothing")

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
        if f.stem not in agent_names or f.stem in BUILTIN_OVERRIDES:
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

# --- the chain has exactly two gates ----------------------------------------
#
# Gates creep back one skill at a time, and each addition looks locally
# reasonable -- "surely THIS one needs a yes". Nine skills carried approval
# machinery before 2026-08-04; the collapse to two is only durable if a tenth
# fails the build.
#
# Asserted on `AskUserQuestion`, because that is the mechanism that actually stops
# and waits. Prose saying "ask the user" is not counted -- it cannot block.
#
# The allowed set is small and each entry is a different KIND of thing:
#   writing-plans   gate 1 -- the finished plan
#   code-review     gate 2 -- sign-off on the change
#   brainstormer    NOT a gate. Its clarify/converge calls supply information the
#                   model does not have; removing them would make the spec the
#                   model's own and label it the user's.
#   capability-layer-maintenance is not a gate, and is off the delivery chain. Its ownership does not change
#                   product stage numbering.
#
# `delivering` and `releasing` are absent on purpose: they ask in prose, and their
# approvals are a standing safety limit rather than a workflow gate.

GATE_SKILLS = {"writing-plans", "releasing"}
QUESTION_SKILLS = {"brainstormer"}

_prompting = {
    d.name for d in sorted(SKILLS.iterdir()) if d.is_dir()
    and "AskUserQuestion" in (d / "SKILL.md").read_text(encoding="utf-8")
}
_unexpected = sorted(_prompting - GATE_SKILLS - QUESTION_SKILLS)
check("no skill prompts the user outside the two gates and two question skills",
      not _unexpected,
      f"{_unexpected} added a gate -- the chain allows two, see workflow.md")

for _g in sorted(GATE_SKILLS):
    check(f"gate skill `{_g}` still has its prompt", _g in _prompting,
          "a gate was removed; the chain would then have no human checkpoint here")

for _skill in ("task-brief", "no-slop"):
    _body = (SKILLS / _skill / "SKILL.md").read_text(encoding="utf-8")
    check(f"`{_skill}` opens no dialogue", "AskUserQuestion" not in _body,
          "its approval gate was removed on 2026-08-04; this re-adds it")


print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
_total = sum(DESC_BUDGET)
print(f"description budget: {_total} chars across {len(DESC_BUDGET)} skills "
      f"(~{_total // 4} tokens injected every turn, mean "
      f"{_total // max(len(DESC_BUDGET), 1)})")
print(f"All skill-layer tests passed ({len(skill_names)} skills, "
      f"{len(agent_files)} agents)")

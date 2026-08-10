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

# Imported once, here, and its absence is a FAILURE rather than a note.
#
# It used to be imported at three sites inside `try/except ImportError`, and the
# handler printed "NOTE: pyyaml missing -- frontmatter checks skipped, not
# passed" and `break`. So on any machine without pyyaml this suite skipped every
# per-skill frontmatter check -- description, trigger properties, tool grants,
# gate markers -- and still EXITED 0. A green that means nothing is exactly what
# `.claude/constitution.md` Article V forbids, and packaging made it reachable:
# a fresh `pip install` into an environment without the dependency declared
# would have produced a silent, confident pass.
try:
    import yaml
except ImportError:  # pragma: no cover - the failure is the point
    yaml = None

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
# name -> description, for the cross-skill collision check after the loop.
DESCRIPTIONS: dict[str, str] = {}
for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
    text = (d / "SKILL.md").read_text(encoding="utf-8")
    if yaml is None:
        check("pyyaml is installed", False,
              "run: pip install pyyaml -- without it every per-skill frontmatter "
              "check below is unrunnable, and reporting that as a pass is the "
              "silent degradation Article V forbids")
        break
    try:
        front = yaml.safe_load(text.split("---", 2)[1])
    except Exception as exc:  # noqa: BLE001 - any parse failure is the finding
        check(f"{d.name} frontmatter parses", False, str(exc)[:80])
        continue
    check(f"{d.name} frontmatter parses to a mapping", isinstance(front, dict))
    if not isinstance(front, dict):
        continue
    desc = front.get("description")
    # `bool(desc)` was the check, and a dict is truthy. An unquoted `: ` inside a
    # description makes YAML parse the scalar as a mapping, so the old assertion
    # passed on a description that had ceased to be one. Introduced and caught on
    # 2026-08-07 by rewriting `delivering` as "...in the repository: branch, PR,
    # merge queue" -- the skill listing rendered it as the bare title `delivering:
    # Delivering`, meaning the description was absent from context and the skill
    # was untriggerable while still listing normally.
    check(f"{d.name} has a non-empty description that is a STRING",
          isinstance(desc, str) and bool(desc.strip()),
          f"description parsed as {type(desc).__name__} -- an unquoted ': ' makes "
          f"YAML read it as a mapping, and the skill silently loses its only "
          f"trigger surface")
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

    # --- the official contract, from code.claude.com/docs/en/skills.md --------
    #
    # Checked here because getting any of these wrong is silent. The layer ran
    # for months with `disable-model-invocation: true` on twelve of thirteen
    # skills, which per the docs means "Claude can invoke: No" -- so every chain
    # handoff was a blocked call and every description was absent from context.
    # Nothing failed. The suite was green the whole time.
    check(f"{d.name} is reachable by the model",
          front.get("disable-model-invocation") is not True,
          "disable-model-invocation: true blocks every handoff INTO this skill "
          "and keeps its description out of context")

    # description + when_to_use share one 1,536-char cap in the skill listing.
    combined = len(str(desc or "")) + len(str(front.get("when_to_use") or ""))
    check(f"{d.name} description+when_to_use under the listing cap",
          combined <= 1536, f"{combined} chars -- the listing truncates at 1536")

    # `context:` accepts `fork`. `false` is not a value, it is a typo that reads
    # as configuration.
    if "context" in front:
        check(f"{d.name} context is a real value", front["context"] == "fork",
              f"context: {front['context']!r} -- the docs define only `fork`")

    check(f"{d.name} pre-approves the tools it needs",
          isinstance(front.get("allowed-tools"), str) and front["allowed-tools"].strip(),
          "without allowed-tools every invocation stops for permission on tools "
          "the skill obviously needs")

    # Pre-approving a write in a layer that installs into unfamiliar repositories
    # means the first edit there lands unannounced. Reads and Bash are fine;
    # Write and Edit should cost one prompt.
    granted = str(front.get("allowed-tools") or "").replace(",", " ").split()
    check(f"{d.name} does not pre-approve Write or Edit",
          not ({"Write", "Edit", "NotebookEdit"} & set(granted)),
          f"granted {sorted({'Write','Edit','NotebookEdit'} & set(granted))}")

    # --- the three properties that decide whether a skill actually fires ------
    #
    # Descriptions are the ONLY trigger surface. Measured on 2026-08-07 across a
    # multi-hour session that touched every stage in the chain: zero skills
    # auto-fired. Not `capability-layer-maintenance` while the layer was being
    # audited and rebuilt, not `systematic-debugging` across eight root-caused
    # bugs, not `verifying-work` on repeated completion claims. Under-triggering
    # is invisible from reading -- the skill simply never runs and the work
    # happens without it -- so the properties correlated with firing are asserted
    # rather than trusted.
    if isinstance(desc, str) and desc:
        DESCRIPTIONS[d.name] = desc

        # 1. Capability first, not a narrative condition.
        #
        # Nine of fourteen opened with a story: "A unit of work finished and the
        # persistent docs no longer match reality", "Work is finished and about to
        # be called done". The matcher compares the task to the description, and a
        # description whose capability arrives in clause three matches it weakly.
        # Anthropic's own example leads with the capability ("Expert code review
        # specialist. Use proactively after writing or modifying code.").
        #
        # A word cap on the first sentence is the mechanical proxy: a narrative
        # condition does not fit in twelve words, and a capability does. Checking
        # for "starts with a verb" was tried first and needs a verb list that is
        # either incomplete or so broad it passes everything.
        first = desc.split(".")[0]
        check(f"{d.name} leads with its capability, not a condition",
              len(first.split()) <= 12,
              f"first sentence is {len(first.split())} words: {first[:70]!r} -- "
              f"lead with what the skill DOES, then the triggers")

        # 2. Enough of the words a person would actually type.
        phrases = re.findall(r'"([^"]+)"', desc)
        check(f"{d.name} lists at least 6 trigger phrases",
              len(phrases) >= 6,
              f"only {len(phrases)} -- these are the literal strings a user "
              f"types, and they are what the description is matched on")

        # 3. An explicit instruction to fire without being asked.
        #
        # `guide/how_to_create_subagents.md`: "Use proactively after X" and "use
        # when Y" phrasing measurably improves automatic delegation. Six of
        # fourteen had no such clause, and the documented consequence is the model
        # doing the work inline instead -- which is what the session above did.
        check(f"{d.name} says to fire without being asked",
              re.search(r"Use this whenever|Use this proactively", desc) is not None,
              "no proactive-use clause -- without one the model does the work "
              "inline and the skill never competes")

    # --- a skill states an ordered procedure ---------------------------------
    #
    # The property, not the heading. `templates/Skills.md` asked for a literal
    # `## Instructions`, but six skills here carry headings that say more than
    # that word does -- `## Three preconditions, checked in order`, `## Phase 1 —
    # Root cause` -- and Anthropic's own published skills use the same descriptive
    # style. Renaming them would trade information for conformance.
    #
    # What actually matters is that the reader can follow a sequence. Two skills
    # had no ordered procedure at all when this was first measured, which is the
    # defect a heading check would have missed while both passed.
    _body = text.split("---", 2)[2]
    # `### A1.` / `### C3.` -- a stage letter plus a step number. Added when
    # `writing-plans` absorbed framing and grew three lettered stages; its steps
    # are ordered and numbered, and the pattern set simply did not see them.
    # This widens what counts as ordering, not how much is required: the
    # threshold below is unchanged at three, and a skill with no sequence at all
    # still fails.
    _ordered = (len(re.findall(r"(?m)^\s{0,3}\d+\.\s", _body))
                + len(re.findall(r"(?m)^#{2,3}\s+(?:Phase|Step)\s+\d+", _body))
                + len(re.findall(r"(?m)^#{2,3}\s+[A-Z]\d+\.\s", _body))
                + len(re.findall(r"(?m)^\*\*\d+\.", _body)))
    check(f"{d.name} states an ordered procedure",
          _ordered >= 3,
          f"only {_ordered} ordered step(s) -- a skill is a procedure, and a "
          f"reader cannot follow prose that never says what comes first")

# --- no two skills claim the same trigger phrase ---------------------------
#
# The failure mode that gets WORSE as each description individually improves.
# Two skills both listing "review this" do not each get a fair shot at it; they
# compete, and competition suppresses both -- so the natural response, adding more
# phrases to each, makes the collision more likely rather than less.
#
# Measured clean at the time this was written (84 phrases, zero collisions). It is
# asserted so it stays that way: a phrase is cheap to add and the cost of adding
# an already-claimed one is invisible.
if DESCRIPTIONS:
    _owner: dict[str, set[str]] = {}
    for _name, _desc in DESCRIPTIONS.items():
        for _phrase in re.findall(r'"([^"]+)"', _desc):
            _owner.setdefault(_phrase.lower().strip(), set()).add(_name)
    _clashes = {k: sorted(v) for k, v in _owner.items() if len(v) > 1}
    check(f"no trigger phrase is claimed by two skills "
          f"({len(_owner)} distinct phrase(s))",
          not _clashes,
          f"contested: {list(_clashes.items())[:3]} -- both skills lose, because "
          f"the model has no basis to prefer either")


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

# --- workflow.md's own names resolve --------------------------------------
#
# The resolution check below reads SKILL.md files. `workflow.md` was never in
# scope, so when four audit skills became `code-review` lenses and
# `artifact-review` moved under `writing-plans/references/`, the policy file kept
# naming them and every suite stayed green. Found by hand on 2026-08-07 -- which
# is exactly the failure mode this file exists to make impossible.
#
# Only names that look like a skill reference are checked: backticked,
# lowercase-hyphenated, and not a known non-skill.
_WF = ROOT / ".claude" / "workflow.md"
if _WF.is_file():
    _wf_text = _WF.read_text(encoding="utf-8")
    _wf_names = {m for m in re.findall(r"`([a-z][a-z0-9-]{3,})`", _wf_text)}
    _wf_unknown = sorted(
        n for n in _wf_names
        if n not in NOT_SKILLS
        and not (SKILLS / n).is_dir()
        and not (ROOT / ".claude" / "agents" / f"{n}.md").is_file()
        # paths, filenames and prose compounds are not skill references
        and "." not in n and "/" not in n
    )
    check("every skill named in workflow.md exists",
          not _wf_unknown,
          f"dead: {_wf_unknown} -- workflow.md is policy, and a policy naming a "
          f"skill that was deleted routes work nowhere")


CHAIN_SUCCESSOR = {
    # An entry capability rather than a numbered stage: it runs before stage 1
    # when the repository is unknown, and never again once its map exists. Listed
    # here so its handoff is pinned like every other -- an off-chain skill whose
    # successor nothing asserts is exactly how the chain silently stops.
    "repo-recon": "writing-plans",
    # `brainstormer` is DISPATCHED by writing-plans and returns to it, as of
    # 2026-08-09. Its successor is still writing-plans, so this entry is
    # unchanged in value while its meaning changed entirely: it used to be a
    # handoff along the chain, and it is now a return to the caller. The pinned
    # edge is the same either way, which is why nothing here had to move.
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

# --- stage 1 dispatches, and a dispatch is not a handoff ---------------------
#
# `writing-plans` absorbed `task-brief` on 2026-08-09, and with it the escape
# hatch that made the old two-skill split survivable: when a field cannot be
# filled, stage 1 fetches the answer instead of guessing or handing back.
#
# That escape hatch is the whole reason the merge is safe, so it is asserted
# rather than trusted to prose. Without it the merged skill has one failure mode
# and it is the bad one -- framing an open approach into six fields, which bakes
# the first idea in under a heading that looks agreed.
_wp = (SKILLS / "writing-plans" / "SKILL.md").read_text(encoding="utf-8")

for _dispatched in ("brainstormer", "research", "designer", "repo-recon",
                    "systematic-debugging"):
    check(f"writing-plans can dispatch `{_dispatched}`",
          f"`{_dispatched}`" in _wp,
          "stage 1 must be able to fetch what framing could not fill")

# Ordering is the one dispatch rule with a correctness argument rather than a
# cost argument: brainstormer AFTER the brief is written is brainstorming
# variations on an answer already committed to. The skill must say so.
check("writing-plans dispatches `brainstormer` before writing the brief",
      re.search(r"before\D{0,40}(writing |the brief|`TASK\.md`)", _wp, re.I)
      is not None,
      "an open approach framed first is the anchor stage 2 exists to prevent")

# The six fields moved here from a deleted skill. A merge that drops them is the
# silent half of this change: planning would still work and framing would simply
# stop happening.
for _field in ("Goal", "Constraints", "Inputs", "Outputs", "Done-check",
               "Out-of-scope"):
    check(f"writing-plans still frames `{_field}`", _field in _wp,
          "the six fields came from task-brief and are the framing contract")

check("writing-plans keeps the (inferred) marking that replaced the brief gate",
      "(inferred)" in _wp,
      "the markers are what let framing skip an approval without hiding a guess")

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
#
# `DISPATCHED_STAGES` are numbered in the table but are not links in the walk:
# stage 1 calls them and they return to it, so following successors never visits
# them. Before 2026-08-09 this was a special case for `task-brief` branching;
# it is now a general property, and naming it is what keeps the walk honest --
# a dispatched stage silently dropped from the table would otherwise still pass.
DISPATCHED_STAGES = {"brainstormer"}

linear = [skill for _n, _name, skill in table]
walk, cur = [], linear[0]
while cur:
    walk.append(cur)
    cur = CHAIN_SUCCESSOR.get(cur)
expected = [s for s in linear if s not in DISPATCHED_STAGES]
check("handoff chain visits the table's linear stages in table order",
      walk == expected, f"table={linear}  walk={walk}  expected={expected}")

for _d in sorted(DISPATCHED_STAGES):
    check(f"dispatched stage `{_d}` returns to its caller",
          CHAIN_SUCCESSOR.get(_d) == "writing-plans",
          "a dispatch that does not come back is a handoff wearing another name")

# --- successors a skill must NOT hand to ------------------------------------
#
# `CHAIN_SUCCESSOR` asserts the POSITIVE successor, so nothing checks the edges a
# skill must never take. The original entry guarded `task-brief` ->
# `writing-plans` on the argument that six lines is not a spec; that edge stopped
# existing on 2026-08-09 when one skill took both jobs, and guarding it now would
# forbid a skill from reaching itself.
#
# The two edges below are what the merge leaves worth guarding. Both are skips
# rather than confusions -- a stage jumping over the one that would have caught
# its mistake:
#
#   * `brainstormer` -> `executing-plans` builds a design nobody decomposed, so
#     no file map, no task ordering and no Gate 1.
#   * `repo-recon` -> `brainstormer` decides the approach is open from a map
#     alone. Recon reads; it does not get to conclude. Stage 1 dispatches
#     `brainstormer` when the six fields say so, which is evidence recon does
#     not have.
#
# A mention is allowed only where it is NEGATED -- the skills here explain what
# they refuse, so a bare ban on the name would be unmaintainable.

FORBIDDEN_SUCCESSOR = {
    "brainstormer": ("executing-plans",
                     "a design is not a plan; stage 1 decomposes it and holds Gate 1"),
    "repo-recon": ("brainstormer",
                   "recon reads and does not conclude; stage 1 owns that call"),
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

# The same invariant in the file that OWNS the chain.
#
# Anchored on the `## Entry` section since 2026-08-08, and rewritten on
# 2026-08-09 when the boundary it guarded was deleted rather than defended.
# What it used to assert -- that the entry names two alternatives and routes
# neither into stage 3 -- describes a chain that no longer exists.
#
# The property that replaces it is stronger, because one door can be checked for
# exactly one thing: the Entry section routes named work to stage 1 and to
# nothing else. A second destination there is the drift that matters now, in the
# same way a missing second alternative was the drift that mattered before.
_wf_text = WORKFLOW.read_text(encoding="utf-8")
_paras = [_wf_text.split("## Entry", 1)[1].split("\n## ", 1)[0]] \
    if "## Entry" in _wf_text else []
check("workflow.md has the Entry section that owns the entry rule", bool(_paras),
      "the rule has one owner; without the section it has none")
if _paras:
    check("...and the Entry section routes named work to `writing-plans`",
          "`writing-plans`" in _paras[0],
          "an entry rule that names no owner routes nothing")

    # The off-chain entries are boundaries, not alternatives: an unread
    # repository and a live failure are conditions on the door rather than
    # different doors. Named so a reader is not left inferring them.
    for _boundary in ("repo-recon", "systematic-debugging"):
        check(f"...and it still names the `{_boundary}` boundary",
              f"`{_boundary}`" in _paras[0],
              "a boundary nobody states is one every session re-derives")

    # `brainstormer` must appear as a DISPATCH from stage 1, never as a second
    # entry. The old rule made it a peer of the brief; the merge made it a
    # subroutine, and the difference is whether work can enter the chain without
    # ever being framed.
    check("...and `brainstormer` appears there as a dispatch, not a second door",
          "`brainstormer`" in _paras[0] and "dispatch" in _paras[0].lower(),
          "a second entry is how work reaches a plan without a brief")

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
        if yaml is None:
            break
        try:
            front = yaml.safe_load(text.split("---", 2)[1])
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

    # --- a dispatching skill pre-approves the dispatch tool -----------------
    #
    # The defect this catches, found by audit on 2026-08-07 and green until then:
    # every skill's `allowed-tools` was some subset of Read/Grep/Glob/Bash, and
    # not one granted `Task`. Five skills carried explicit fan-out instructions
    # and eight agents named a dispatching skill in their body, so every
    # documented parallel review stopped for a permission prompt in the middle of
    # the skill that was meant to be running autonomously.
    #
    # The check above already asserts the reverse direction -- that every agent is
    # named by some skill. Nothing asserted that the naming skill could actually
    # reach it. `allowed-tools` is a pre-approval list, not a restriction, so the
    # symptom was an interruption rather than an error: the worst kind, because it
    # looks like the harness asking a reasonable question.
    #
    # `Task` is the tool name in the published skills contract; `Agent` is the
    # name some hosts present. Either satisfies this -- the layer is
    # harness-neutral by `AGENTS.md`, and pinning one host's spelling here would
    # make the check wrong somewhere it is supposed to hold.
    DISPATCH_TOOLS = {"Task", "Agent"}

    def granted_tools(text: str) -> set[str]:
        """The skill's pre-approved tool set. An unparseable header yields the
        empty set, which fails the check below -- the right direction, since a
        header nothing can read grants nothing either."""
        if yaml is None:
            return set()
        parts = text.split("---", 2)
        if len(parts) < 3:
            return set()
        loaded = yaml.safe_load(parts[1])
        if not isinstance(loaded, dict):
            return set()
        return set(str(loaded.get("allowed-tools") or "").replace(",", " ").split())

    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        text = (d / "SKILL.md").read_text(encoding="utf-8")
        body = text.split("---", 2)[-1]
        dispatched = sorted({
            n for n in re.findall(r"`([a-z][a-z0-9]+(?:-[a-z0-9]+)+)`", body)
            if n in agent_names
        })
        approved = granted_tools(text)

        if dispatched:
            check(f"{d.name} pre-approves the dispatch tool it needs for "
                  f"{', '.join(dispatched)}",
                  bool(approved & DISPATCH_TOOLS),
                  f"names {len(dispatched)} agent(s) but grants only "
                  f"{sorted(approved)} -- every dispatch stops for a permission "
                  f"prompt mid-skill, which reads as the harness being careful "
                  f"rather than as the layer being miswired")
        elif approved & DISPATCH_TOOLS:
            # The converse. A stray grant is not dangerous, but it is a claim
            # about the skill that its body does not support, and this layer's
            # whole premise is that such claims get checked.
            check(f"{d.name} grants dispatch and names an agent to dispatch",
                  False, "pre-approves Task but its body names no agent")

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
#
# `brainstormer` was the one exception, on the argument that clarify/converge are
# not gates because they ask "which direction" rather than "may I proceed". True,
# and it did not survive contact: ten blocking questions before any artefact
# exists is the opposite of a two-gate chain whatever they are called. They are
# `[NEEDS CLARIFICATION]` markers now, and `writing-plans` answers all of them in
# ONE call at Gate 1 -- so the exception is gone and the set is exactly two.
#
# `delivering` and `releasing` are absent on purpose: they ask in prose, and their
# approvals are a standing safety limit rather than a workflow gate.

GATE_SKILLS = {"writing-plans", "releasing"}
# Deliberately empty. Any entry here is a third place that stops and waits.
QUESTION_SKILLS: set[str] = set()

# Declared, not inferred.
#
# The check was a substring test for "AskUserQuestion", which worked only while
# the gate skills were the only files naming the tool. It broke the moment a
# skill named it in order to FORBID it -- `brainstormer` now does so four times,
# and the substring test read those prohibitions as a new gate, failing the build
# for removing exactly the dialogue the build exists to keep out.
#
# Matching on syntax cannot fix it either. These two are the real gates:
#
#     into one `AskUserQuestion` call
#     then use `AskUserQuestion` for the single explicit shipment
#
# and these four are prohibitions or references to somebody else's gate:
#
#     Never call `AskUserQuestion` from this skill
#     It carried ten `AskUserQuestion` calls until 2026-08-08
#     in **one** `AskUserQuestion` at Gate 1        <- describes writing-plans
#     Not with `AskUserQuestion`, and not in prose
#
# The difference is negation and referent, not grammar, and a regex that tried to
# read either would be a guess in a safety check. So a gate now DECLARES itself
# with a marker somebody has to type on purpose -- which is also the property
# wanted here, since a tenth gate should be hard to add by accident.
GATE_MARKER = re.compile(r"<!--\s*GATE\s*\d", re.I)
_prompting = {
    d.name for d in sorted(SKILLS.iterdir()) if d.is_dir()
    and GATE_MARKER.search((d / "SKILL.md").read_text(encoding="utf-8"))
}
_unexpected = sorted(_prompting - GATE_SKILLS - QUESTION_SKILLS)
check("no skill prompts the user outside the two gates",
      not _unexpected,
      f"{_unexpected} added a gate -- the chain allows two, see workflow.md")

for _g in sorted(GATE_SKILLS):
    _gbody = (SKILLS / _g / "SKILL.md").read_text(encoding="utf-8")
    check(f"gate skill `{_g}` declares its gate", _g in _prompting,
          "a gate was removed; the chain would then have no human checkpoint here")
    # The marker is a claim; the call is the mechanism. A marker with no
    # AskUserQuestion beside it is a gate that announces itself and never stops.
    check(f"gate skill `{_g}` actually calls the tool it declares",
          "AskUserQuestion" in _gbody,
          "the marker says there is a gate here and nothing implements it")

# --- anything that leaves the machine asks with the tool ---------------------
#
# The two-gate rule is about LIFECYCLE approvals, and it was read for months as
# "only two skills may ever call AskUserQuestion". `delivering` -- whose triggers
# are "push this up", "merge it", "ship it" -- therefore had none, and said so
# outright: "No separate delivery approval exists; shipment approval is owned by
# `releasing`." But `releasing` runs AFTER delivery, so the click authorising a
# push arrived after the push, while `CLAUDE.md` forbade pushing without explicit
# approval and `/publish` gated the same action with two calls. One action, two
# rules, decided by which entry point you took.
#
# An outward-facing operation is an operational safety check, not a gate: no
# `<!-- GATE n -->` marker, so the gate set below is still exactly two.
OUTWARD_SKILLS = {
    "delivering": "push, PR and merge",
    "releasing": "deploy",
}
# --- the stage that hands off to a merge says who actually merges ------------
#
# No skill in this layer runs `gh pr merge`; a human presses the button. That was
# only ever implied -- `delivering` said "prepare the PR or merge-queue handoff"
# and `/publish` said "landing is delivering's business and the queue's", so each
# pointed at the other and at a merge queue that answers 403 on a free private
# repository. A step handed to a mechanism that may not exist is nobody's.
#
# Also pinned: the squash-vs-stack incompatibility. `CLAUDE.md` says `wip:`
# checkpoints exist because squash-merge collapses them, which is true for one PR
# and is exactly what breaks a stack -- squashing the base gives `main` a new SHA
# and every child then re-proposes its parent's files as conflicts. Discovered
# with five stacked PRs already open.
_del = (SKILLS / "delivering" / "SKILL.md").read_text(encoding="utf-8")
check("`delivering` says no skill merges",
      re.search(r"no skill.{0,40}merge|human presses the button", _del, re.I | re.S)
      is not None,
      "deferring to a merge queue that may not exist leaves the merge unowned")
# A validator nothing invokes is the gate-nobody-runs failure this layer keeps
# deleting. `delivery_check.py` is advisory by construction -- the 403 means it
# can never prevent a merge -- so its entire value is that this stage runs it.
check("`delivering` runs the delivery preflight",
      "tools/delivery_check.py" in _del,
      "the check exists and nothing calls it, which is worth less than no check "
      "because it reads as coverage")
check("...and treats a failing preflight as a stop",
      re.search(r"exit `?1`?[^.]{0,40}stop", _del, re.I) is not None,
      "an advisory that never stops anything is a log line")

check("`delivering` warns that squash breaks a stacked PR",
      "squash" in _del.lower() and "stack" in _del.lower(),
      "the layer assumes squash-merge and says nothing about what that does to a "
      "stack, which is the one place the two interact badly")

# Nothing may quietly acquire the ability to merge. `_MERGE_VERBS` are checked
# across every skill and command, and a mention only passes where it is negated.
_MERGE_VERBS = re.compile(r"(?<![`\w])gh pr merge(?![\w])")
for _p in sorted([*SKILLS.glob("*/SKILL.md"),
                  *(ROOT / ".claude" / "commands").glob("*.md")]):
    _t = _p.read_text(encoding="utf-8")
    _hits = [ln for ln in _t.splitlines() if _MERGE_VERBS.search(ln)
             and not re.search(r"\b(never|not|no|nor)\b", ln, re.I)]
    check(f"{_p.parent.name}/{_p.name} does not merge", not _hits,
          f"{_hits[:1]} -- merging is the human's, and it is the one action "
          f"the chain deliberately does not automate")


for _skill, _what in sorted(OUTWARD_SKILLS.items()):
    _body = (SKILLS / _skill / "SKILL.md").read_text(encoding="utf-8")
    check(f"`{_skill}` confirms {_what} with AskUserQuestion",
          "AskUserQuestion" in _body,
          "a prose question is answerable by silence and scrolls away; this "
          "operation is irreversible and outward-facing")
    # The prohibition has to be explicit, or the next editor reads the call as
    # optional politeness and drops it during a tidy-up.
    check(f"...and `{_skill}` says a prose question does not count",
          re.search(r"prose question", _body, re.I) is not None,
          "the rule is the tool, not the asking")
# --- a skill's claim about another skill's output must be true ---------------
#
# `executing-plans` says: "Tick `- [ ]` -> `- [x]` as each step lands.
# `writing-plans` mandates that syntax expressly for tracking." It did not. The
# task template emitted `**Done when:**` and no checkbox, so every plan in
# docs/plans/ had zero of them and the executor's whole progress mechanism had
# never once had anything to tick. Every suite stayed green, because nothing
# checked that one skill's claim ABOUT another was accurate -- only that the
# names it used resolved to real skills.
#
# The general property is untestable (arbitrary prose about arbitrary prose).
# This pins the instance in the direction that matters: a consumer naming a
# syntax must have a producer that actually emits it.
_ep = (SKILLS / "executing-plans" / "SKILL.md").read_text(encoding="utf-8")
_wp_all = "\n".join(
    p.read_text(encoding="utf-8")
    for p in [SKILLS / "writing-plans" / "SKILL.md",
              *sorted((SKILLS / "writing-plans" / "references").glob("*.md"))])

if "- [ ]" in _ep:
    check("the checkbox `executing-plans` ticks is one `writing-plans` emits",
          "- [ ]" in _wp_all,
          "the consumer names a progress syntax the producer never writes")
    check("...and `writing-plans` emits it as a per-task progress block",
          re.search(r"- \[ \]\s+Task\s+\d", _wp_all) is not None,
          "a checkbox somewhere is not a checkbox per task; tools/analyze.py "
          "counts them against the task headings")


for _skill in ("no-slop", "brainstormer"):
    _body = (SKILLS / _skill / "SKILL.md").read_text(encoding="utf-8")
    # Mentions are allowed -- these files explain what they must NOT do, and
    # brainstormer names the tool three times to forbid it. A CALL is the thing
    # being banned, so the check is for the invocation shape, not the word.
    _calls = re.findall(r"(?<![`\w])AskUserQuestion\s*\(", _body)
    check(f"`{_skill}` opens no dialogue", not _calls,
          f"{len(_calls)} call(s) -- the chain stops in two places and this is "
          f"not one of them")



# --- the entry rule is owned in one place, or it is owned nowhere ------------
#
# `workflow.md` §Entry says of itself: "This section owns the entry rule. Nowhere
# else states it."
#
# This check was written on 2026-08-08 for a two-branch rule, where the failure
# was a skill naming ONE branch as though it were the whole thing -- `no-slop`
# sent every structural finding to a brief, so a finding whose approach was open
# got the anchor instead of the design.
#
# The merge on 2026-08-09 removed the second branch, which removes that exact
# failure and leaves the inverse one. With one door, the way to restate the rule
# wrongly is to name `brainstormer` as an entry -- work that reaches a design
# without ever being framed, and so reaches a plan with no `TASK.md` behind it.
# Same property, opposite polarity: a skill routing INTO the chain must not name
# a stage that is dispatched rather than entered.
#
# Naming stage 1 is correct. Deferring to the section that owns the rule is
# correct. Naming `brainstormer` alone is the defect.

ENTRY_PAIR = ("writing-plans", "brainstormer")
# A paragraph, or a single list item. A bullet is a standalone claim -- a reader
# scanning `## Routing` reads one line and acts on it -- so it is checked alone
# even when the bullets around it say more.
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n|\n(?=\s*[-*] )")
_entry_failures: list[str] = []

for _path in sorted(SKILLS.glob("*/SKILL.md")):
    _name = _path.parent.name
    if _name in ENTRY_PAIR:
        continue                      # the two branches may name themselves
    _body = _path.read_text(encoding="utf-8")
    # Scope: the sections that DECLARE handoffs, at paragraph granularity.
    #
    # Two wrong granularities were tried first, and each failed in the opposite
    # direction. Per FILE asked whether `brainstormer` appeared anywhere, so one
    # correct paragraph absolved every other -- `no-slop` deferred to §Entry in
    # its body and went on routing unconditionally in `## Routing` and
    # `## Success`, and the check passed. Per SENTENCE then flagged `repo-recon`,
    # whose `## Next step` names `task-brief` in one sentence and explains the
    # branch to `brainstormer` two sentences later, which is a complete and
    # correct statement of the rule.
    #
    # Sections, because a handoff declared outside them is narrative -- line 17 of
    # `repo-recon` says the chain "used to start at `task-brief`", which is
    # history, not routing. `FORBIDDEN_SUCCESSOR` above scopes itself the same
    # way for the same reason.
    for _section in ("## Routing", "## Next step", "## Success"):
        _start = _body.find(_section)
        if _start < 0:
            continue
        _end = _body.find("\n## ", _start + len(_section))
        _text = _body[_start:_end if _end > 0 else len(_body)]
        for _para in _PARAGRAPH_SPLIT.split(_text):
            if "`brainstormer`" not in _para:
                continue
            if "`writing-plans`" in _para or "Entry" in _para:
                continue      # names the door, or defers to the section owning it
            if _NEGATED.search(_para):
                continue      # "not a stage entered beside stage 1"
            if "dispatch" in _para.lower():
                continue      # states the relationship correctly on its own
            _entry_failures.append(
                f"{_name} {_section}: {' '.join(_para.split())[:70]}")

check("no skill states half the entry rule",
      not _entry_failures,
      f"{_entry_failures} route to `brainstormer` without naming `writing-plans`, "
      f"calling it a dispatch, or deferring to workflow.md §Entry -- there is one "
      f"door as of 2026-08-09, and a second one lets work reach a plan unframed")

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

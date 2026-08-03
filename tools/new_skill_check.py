#!/usr/bin/env python3
"""Is one skill actually reachable? Checks every wiring point for a single skill.

    python tools/new_skill_check.py <name>
    python tools/new_skill_check.py --all

Why this exists
---------------
`test_process_router.py` proves the layer is internally consistent, over every
skill at once. That is the right check for CI and the wrong one for authoring:
when it goes red it names a property, not the file you forgot, and when it goes
green it says nothing about whether the skill you just wrote can be reached.

The failure this is aimed at is silence. A skill with a mismatched frontmatter
`name:`, or a flat `.claude/skills/<name>.md`, or no routing entry, does not
error -- it simply never appears. Five files have to agree, and the only symptom
of disagreement is a skill that never fires.

So this reports per wiring point, names the file to edit for each failure, and
finishes by actually firing the router at the skill's own keywords. Structure
green and reachability red is the normal outcome for a freshly written skill, and
the two are worth separating.

Exit code is 0 only when every REQUIRED row passes. Advisory rows print but never
fail the run.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
ROUTING = ROOT / ".claude" / "routing" / "process-skills.md"
WORKFLOW = ROOT / ".claude" / "workflow.md"
CLAUDE_MD = ROOT / "CLAUDE.md"
ROUTER = ROOT / ".claude" / "hooks" / "pre-run" / "05-process-skill-router.py"

# Same numbers the suite enforces, quoted from the same reasoning: 1024 chars is
# the hard frontmatter spec limit, and ~380 chars of description is the per-turn
# injection budget rather than a style preference.
HARD_FRONTMATTER = 1024
SOFT_DESCRIPTION = 400
HARD_DESCRIPTION = 500

MODELS = {"opus", "sonnet", "haiku"}
EFFORTS = {"low", "medium", "high"}


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str, str, bool]] = []

    def need(self, what: str, ok: bool, detail: str = "", fix: str = "") -> None:
        self.rows.append((what, ok, detail, fix, True))

    def note(self, what: str, ok: bool, detail: str = "", fix: str = "") -> None:
        self.rows.append((what, ok, detail, fix, False))

    def failed(self) -> list[tuple[str, bool, str, str, bool]]:
        return [r for r in self.rows if r[4] and not r[1]]

    def render(self, name: str) -> int:
        width = max(len(r[0]) for r in self.rows) + 2
        print(f"\nskill: {name}\n")
        for what, ok, detail, _fix, required in self.rows:
            mark = "PASS" if ok else ("FAIL" if required else "note")
            tail = f"  {detail}" if detail else ""
            print(f"  {mark}  {what:<{width}}{tail}")
        bad = self.failed()
        if bad:
            print(f"\n{len(bad)} required check(s) failed. Edit these:\n")
            for what, _ok, _d, fix, _r in bad:
                print(f"  - {what}")
                if fix:
                    print(f"      {fix}")
            return 1
        advisory = [r for r in self.rows if not r[4] and not r[1]]
        print(f"\nAll {sum(1 for r in self.rows if r[4])} required check(s) pass"
              + (f"; {len(advisory)} advisory note(s) above." if advisory else "."))
        return 0


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """The YAML block, flat key: value only -- same shape the harness reads."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}, ""
    raw = m.group(1)
    out: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out, raw


def routing_entries() -> dict[str, list[str]]:
    """`## <skill>` -> its keywords. Mirrors the hook's own parser."""
    if not ROUTING.is_file():
        return {}
    text = ROUTING.read_text(encoding="utf-8", errors="ignore")
    out: dict[str, list[str]] = {}
    for block in re.split(r"^## +", text, flags=re.M)[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        skill = lines[0].strip().lower()
        if not skill or len(skill.split()) != 1:
            continue
        m = re.search(r"^Keywords:\s*(.+)$", block, re.M)
        if not m:
            out[skill] = []
            continue
        out[skill] = [k.strip().lower() for k in m.group(1).split(",") if k.strip()]
    return out


def fire_router(prompt: str) -> str:
    """Run the real hook, so this reports what the session would see."""
    try:
        p = subprocess.run(
            [sys.executable, str(ROUTER)],
            input=f'{{"prompt": {prompt!r}}}'.replace("'", '"'),
            capture_output=True, text=True, timeout=30,
        )
        return p.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def check(name: str) -> int:
    r = Report()
    skill_dir = SKILLS / name
    skill_md = skill_dir / "SKILL.md"
    all_dirs = {d.name for d in SKILLS.iterdir() if d.is_dir()} if SKILLS.is_dir() else set()

    # --- 1. the file exists, in the shape the harness looks for --------------
    flat = SKILLS / f"{name}.md"
    r.need("directory .claude/skills/<name>/ exists", skill_dir.is_dir(),
           "" if skill_dir.is_dir() else "missing",
           f"mkdir {skill_dir.relative_to(ROOT)}")
    r.need("SKILL.md, not a flat <name>.md", skill_md.is_file(),
           "flat file found -- it will never appear" if flat.is_file() else
           ("" if skill_md.is_file() else "missing"),
           f"move it to {skill_md.relative_to(ROOT)}")
    if not skill_md.is_file():
        return r.render(name)

    text = skill_md.read_text(encoding="utf-8", errors="ignore")
    fm, raw = parse_frontmatter(text)

    # --- 2. frontmatter -----------------------------------------------------
    r.need("frontmatter parses", bool(fm), "" if fm else "no --- block at the top",
           "the block must be the first thing in the file")
    fm_name = fm.get("name", "")
    r.need("frontmatter name matches the directory", fm_name == name,
           f"name: {fm_name!r} vs dir {name!r}" if fm_name != name else "",
           "a mismatch makes the skill invisible with no error")

    desc = fm.get("description", "")
    r.need("description present", bool(desc))
    r.need("description states a 'Do NOT use' clause",
           "do not use" in desc.lower(),
           "" if "do not use" in desc.lower() else "absent",
           "without it the router names this skill and its neighbour together")
    r.note(f"description <= {SOFT_DESCRIPTION} chars (injected every turn)",
           len(desc) <= SOFT_DESCRIPTION, f"{len(desc)} chars",
           "put trigger breadth in process-skills.md, which costs nothing")
    r.need(f"description <= {HARD_DESCRIPTION} chars", len(desc) <= HARD_DESCRIPTION,
           f"{len(desc)} chars")
    r.need(f"frontmatter <= {HARD_FRONTMATTER} chars", len(raw) + 8 <= HARD_FRONTMATTER,
           f"{len(raw) + 8} chars")
    r.need("model is one of opus/sonnet/haiku", fm.get("model", "") in MODELS,
           f"model: {fm.get('model', '(absent)')!r}")
    r.need("effort is one of low/medium/high", fm.get("effort", "") in EFFORTS,
           f"effort: {fm.get('effort', '(absent)')!r}")

    # --- 3. routing entry ---------------------------------------------------
    entries = routing_entries()
    words = entries.get(name)
    r.need("has a `## <name>` entry in routing/process-skills.md", words is not None,
           "" if words is not None else "absent -- the build fails without it",
           f"add a '## {name}' heading to {ROUTING.relative_to(ROOT)}")
    r.need("that entry has a non-empty Keywords: line", bool(words),
           "" if words else "heading with no keywords is silently skipped",
           "one 'Keywords:' line, comma separated")

    if words:
        upper = [w for w in words if w != w.lower()]
        r.need("every keyword is lowercase", not upper, ", ".join(upper[:4]),
               "the hook lowercases the prompt but not the file")

        # Collisions and containment, against every OTHER skill's keywords.
        others = {w: s for s, ws in entries.items() if s != name for w in ws}
        dupes = [w for w in words if w in others]
        r.need("no keyword is already claimed by another skill", not dupes,
               "; ".join(f"{w!r} ({others[w]})" for w in dupes[:4]))
        contained = [f"{w!r} contains {o!r} ({others[o]})"
                     for w in words for o in others if o in w and o != w]
        contained += [f"{o!r} ({others[o]}) contains {w!r}"
                      for w in words for o in others if w in o and o != w]
        r.need("no keyword contains another skill's keyword", not contained,
               "; ".join(contained[:3]),
               "either one makes the router name two skills for one prompt")

    # --- 4. workflow.md and CLAUDE.md ---------------------------------------
    wf = WORKFLOW.read_text(encoding="utf-8", errors="ignore") if WORKFLOW.is_file() else ""
    in_chain = re.search(rf"^\|\s*(\d+)\s*\|[^|]+\|\s*`{re.escape(name)}`", wf, re.M)
    in_offchain = re.search(rf"^\|[^|\d]+\|\s*`{re.escape(name)}`\s*\|", wf, re.M)
    r.need("workflow.md gives it a row (chain table or off-chain table)",
           bool(in_chain or in_offchain),
           "numbered stage " + in_chain.group(1) if in_chain else
           ("off-chain" if in_offchain else "no row"),
           f"add a row to {WORKFLOW.relative_to(ROOT)}")

    if in_chain:
        stage = int(in_chain.group(1))
        # Advisory, not required, and deliberately so: test_process_router.py
        # asserts this line only `if` present ("only the stages that claim a
        # number are asserted"), and 5 of the 10 on-chain skills do not carry
        # one. Making it required here would impose a policy the repo has not
        # adopted, on a checker whose job is to report the layer's rules rather
        # than invent them. It is worth seeing, so it prints.
        stated = re.search(r"Workflow stage (\d+)", text)
        r.note("states its own 'Workflow stage N' (optional; 5 of 10 do not)",
               bool(stated), "absent" if not stated else f"stage {stated.group(1)}")
        if stated:
            r.need("that number matches workflow.md",
                   int(stated.group(1)) == stage,
                   f"skill says {stated.group(1)}, table says {stage}")
        # Stage 1 has no predecessor. Asserting one made task-brief fail a
        # condition it cannot satisfy -- a checker bug, not a layer defect.
        if stage > 1:
            r.need("the predecessor names it in a `## Next step`",
                   _has_predecessor(name, wf, stage),
                   "no earlier stage hands off to it",
                   "without this the chain stops one stage early and looks complete")

    cm = CLAUDE_MD.read_text(encoding="utf-8", errors="ignore") if CLAUDE_MD.is_file() else ""
    r.need("CLAUDE.md Skills table names it", f"`{name}`" in cm,
           "" if f"`{name}`" in cm else "absent",
           f"add a row to the Skills table in {CLAUDE_MD.name}")

    # --- 5. every skill it names in backticks resolves -----------------------
    agents = {f.stem for f in (ROOT / ".claude" / "agents").glob("*.md")}
    named = set(re.findall(r"`([a-z][a-z-]{3,})`", text))
    # Names that look like skills but are not: hook dirs, commands, doc files,
    # Claude Code's own agent types, and review angles that read like nouns.
    ignore = {d.name for d in (ROOT / ".claude" / "hooks").iterdir() if d.is_dir()}
    ignore |= {f.stem for f in (ROOT / ".claude" / "commands").glob("*.md")}
    ignore |= {"general-purpose", "test-quality", "scope-creep", "pre-commit",
               "on-artifact-create", "hard-gate", "no-op", "read-only"}
    dangling = sorted(n for n in named
                      if n not in all_dirs and n not in agents and n not in ignore
                      and "-" in n and n.count("-") <= 2
                      and not n.endswith((".md", ".py", ".json")))
    r.note("hyphenated backticked names all resolve to a skill or agent",
           not dangling, ", ".join(dangling[:6]),
           "check these are not skills you meant to name")

    # --- 6. reachability: fire the real router ------------------------------
    hit = ""
    if words:
        out = fire_router(words[0])
        hit = words[0] if f"`{name}`" in out else ""
        if not hit:
            for w in words[1:6]:
                if f"`{name}`" in fire_router(w):
                    hit = w
                    break
    r.need("the router actually names it when fired at its own keywords",
           bool(hit), f"matched on {hit!r}" if hit else "no keyword reached it",
           "structure can be green while the skill is reachable by nothing")

    return r.render(name)


def _has_predecessor(name: str, wf: str, stage: int) -> bool:
    """Does any earlier-stage skill name this one in a `## Next step` section?"""
    table = re.findall(r"^\|\s*(\d+)\s*\|[^|]+\|\s*`([a-z-]+)`", wf, re.M)
    earlier = [s for n, s in table if int(n) < stage]
    for other in earlier:
        p = SKILLS / other / "SKILL.md"
        if not p.is_file():
            continue
        body = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^## Next step.*?(?=^## |\Z)", body, re.S | re.M)
        if m and f"`{name}`" in m.group(0):
            return True
    return False


def main() -> int:
    args = [a for a in sys.argv[1:] if a]
    if not args:
        print(__doc__.strip().splitlines()[2].strip())
        print("       python tools/new_skill_check.py --all")
        return 2
    if args[0] == "--all":
        names = sorted(d.name for d in SKILLS.iterdir() if d.is_dir())
        rc = 0
        for n in names:
            rc |= check(n)
        print(f"\n{len(names)} skill(s) checked.")
        return rc
    if not (SKILLS / args[0]).exists() and not (SKILLS / f"{args[0]}.md").exists():
        print(f"FAIL: no skill named {args[0]!r} under .claude/skills/")
        print("      existing: " + ", ".join(
            sorted(d.name for d in SKILLS.iterdir() if d.is_dir())))
        return 1
    return check(args[0])


if __name__ == "__main__":
    sys.exit(main())

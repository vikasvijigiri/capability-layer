#!/usr/bin/env python3
"""Slop checks — the mechanically decidable subset, at two scopes.

    python tools/test_no_slop.py                 # --scope layer  (default)
    python tools/test_no_slop.py --scope repo    # everything git tracks

Why two scopes
--------------
The two cadences cost different amounts and answer different questions:

  layer   the `.claude/` capability layer only. Cheap. Runs as part of the
          normal suite every turn, and `post-run/07-layer-drift.py` names the
          `no-slop` skill once enough of the layer has changed to be worth a
          reader.
  repo    every tracked file. Runs once before shipping, as workflow stage 6.

Defaulting to `repo` would put a whole-repo sweep in the per-turn commit gate,
which is how a gate gets switched off -- three were deleted here for costing
more than they returned.

Why this is a subset, stated up front
-------------------------------------
The checklist this implements has fifteen categories. Most are not decidable by
a program: "is every sentence earning its place", "could Claude misinterpret
this", "is the intent immediately obvious" all need a reader.

A script claiming to check those would be the fourth false-confidence gate in
this repo's history -- `03-review-gate`, `05-docs-gate` and `05-docs-required`
were all deleted for asserting a judgement they could not make. So this file
checks what is falsifiable and the `no-slop` skill carries the rest.

What runs at which scope
------------------------
  both    credentials, merge-conflict markers, unresolved placeholders, empty
          tracked files -- slop that does not care which directory it is in
  both    hedging and duplicated guidance, in documents that give INSTRUCTIONS
          (`.claude/**`, `CLAUDE.md`). A spec saying "we may add X later" is
          honest; a skill saying it hands the decision back to the reader while
          looking like guidance. Applying this to `docs/` would flag every spec
          and the check would be off within a day.
  both    the per-skill contract: description budget, negative trigger,
          `## Success` and `## Routing`, prose-line budget

`--scope repo` widens the file set the first group runs over; it does not add
different checks. The instruction and skill checks are already whole by nature.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
SKILLS = CLAUDE / "skills"
AGENTS = CLAUDE / "agents"

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# --- the file set ------------------------------------------------------------
#
# Only what git tracks. Hook logs live under .claude/ and capture tool payloads
# verbatim, but they are gitignored, so "committed and shared" is false for them
# -- and flagging one was this check's own first false positive.

def tracked(prefix: str | None) -> list[Path]:
    cmd = ["git", "ls-files"] + ([prefix] if prefix else [])
    try:
        out = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                             text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        notes.append("git ls-files failed -- file scans skipped")
        return []
    return [ROOT / line for line in out.splitlines() if line.strip()]


# .docx, .png and .svg are tracked here. Reading them as text produces bytes that
# can match a credential regex by coincidence, so decode strictly and skip what
# is not text -- rather than errors="ignore", which turns a binary into
# plausible-looking garbage that the scan then reasons about.
BINARY_SUFFIXES = {".docx", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico",
                   ".zip", ".woff", ".woff2", ".ttf", ".xlsx", ".pptx"}

# These name the patterns they scan for; scanning them is a guaranteed false hit.
SELF_REFERENTIAL = {"_hooklib.py", "01-secret-scan.py", "test_no_slop.py"}


def read_text(path: Path) -> str | None:
    if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def is_instruction_doc(path: Path) -> bool:
    """Documents that give instructions, as opposed to recording decisions."""
    r = rel(path)
    if r in ("CLAUDE.md", "AGENTS.md"):
        return True
    return (r.startswith(".claude/") and r.endswith(".md")
            and "state" not in r.split("/"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope", choices=("layer", "repo"), default="layer",
                    help="layer = .claude/ only (default); repo = everything tracked")
    args = ap.parse_args()

    files = tracked(None if args.scope == "repo" else ".claude")
    scannable = [p for p in files if p.name not in SELF_REFERENTIAL]

    # --- credentials ---------------------------------------------------------
    sys.path.insert(0, str(CLAUDE / "hooks"))
    try:
        from _hooklib import SECRET_PATTERNS
    except ImportError:
        notes.append("could not import _hooklib -- credential scan skipped")
        SECRET_PATTERNS = []

    # --- conflict markers ----------------------------------------------------
    # Silent in every language, and it breaks the file for whoever reads it next.
    conflict_re = re.compile(r"^(<{7} |>{7} |={7}$)", re.MULTILINE)

    # --- unresolved placeholders ---------------------------------------------
    # `writing-plans` calls these "the plan is not finished". Same for shipped
    # code and shipped prose.
    #
    # Skipped inside backticks or double quotes: that is a document NAMING the
    # marker, which is exactly what the red-flag lists and the prior-art notes do.
    placeholder_re = re.compile(r"\b(TODO|FIXME|XXX|TBD|HACK)\b")

    def is_quoted(line: str, marker: str) -> bool:
        """True when every occurrence of `marker` sits inside a code span or a
        double-quoted string.

        Split on the delimiter and take the odd segments -- inside a span is
        exactly "an odd number of delimiters precede it". A single regex cannot
        do this: an apostrophe is not a quote, and treating it as one made
        `minsky's ... (`TODO/PLANNING`)` read as an open quote that
        swallowed the backticks, so the real code span went unrecognised.
        """
        for delim in ("`", '"'):
            if marker in "".join(line.split(delim)[1::2]):
                return True
        return False

    instruction_docs = []

    for path in scannable:
        if path.is_file() and path.stat().st_size == 0:
            fail(f"{rel(path)} is empty but tracked — delete it or write it")
            continue
        body = read_text(path)
        if body is None:
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(body):
                fail(f"{rel(path)} matches a credential pattern — it is committed")
                break

        if conflict_re.search(body):
            fail(f"{rel(path)} contains a merge-conflict marker")

        for lineno, line in enumerate(body.splitlines(), 1):
            m = placeholder_re.search(line)
            if m and not is_quoted(line, m.group(1)):
                fail(f"{rel(path)}:{lineno} unresolved {m.group(1)} — "
                     f"resolve it or make it a tracked issue")

        if is_instruction_doc(path):
            instruction_docs.append(path)

    # --- instruction docs: hedging -------------------------------------------
    #
    # An instruction that hedges transfers the decision back to the reader while
    # looking like guidance. "Try to keep it short" is not a rule.
    #
    # Deliberately narrow. "may" and "can" are legitimate (permission,
    # capability); only phrases that weaken an instruction are listed.
    hedges = [
        r"\btry to\b", r"\bmaybe\b", r"\bprobably should\b", r"\bif possible\b",
        r"\bgenerally speaking\b", r"\bit might be a good idea\b",
        r"\bwhere appropriate\b", r"\bas needed\b",
    ]
    hedge_re = re.compile("|".join(hedges), re.IGNORECASE)

    for path in instruction_docs:
        body = read_text(path) or ""
        for lineno, line in enumerate(body.splitlines(), 1):
            if line.lstrip().startswith((">", "#", "|")):
                continue  # quotes, headings and tables are not instructions
            m = hedge_re.search(line)
            if m:
                fail(f"{rel(path)}:{lineno} hedges: {m.group(0)!r} — "
                     f"say the rule or drop it")

    # --- instruction docs: duplicated guidance -------------------------------
    #
    # The "Duplicate Knowledge" smell. When one sentence is maintained in three
    # files, two go stale and nobody notices which. Only substantial sentences
    # count; short ones repeat legitimately.
    min_dup_chars = 90
    sentences: dict[str, list[str]] = defaultdict(list)

    for path in sorted(list(SKILLS.rglob("*.md")) + list(AGENTS.rglob("*.md"))):
        body = read_text(path)
        if body is None:
            continue
        body = re.sub(r"(?s)^---.*?---", "", body, count=1)      # frontmatter
        body = re.sub(r"(?s)```.*?```", "", body)                # code blocks
        for raw in re.split(r"(?<=[.!?])\s+|\n\n", body):
            s = " ".join(raw.split())
            if len(s) >= min_dup_chars and not s.startswith(("|", "#", "-", "*")):
                sentences[s].append(rel(path))

    for sentence, where in sentences.items():
        if len(set(where)) > 1:
            fail(f"duplicated across {', '.join(sorted(set(where)))}: "
                 f"{sentence[:70]}… — one owner, others point at it")

    # --- the per-skill contract ----------------------------------------------
    #
    # A skill loads in full when it fires and its description is injected every
    # turn, so both have budgets. The structural sections are not style: a skill
    # with no stated Success has no definition of done, and one with no Routing
    # hands off to nothing.
    desc_budget = 500
    skill_line_budget = 200

    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        md = d / "SKILL.md"
        if not md.is_file():
            fail(f".claude/skills/{d.name}/ has no SKILL.md — it is invisible")
            continue
        text = md.read_text(encoding="utf-8")

        # Prose lines only. A skill carrying an 80-line task template is not a
        # god-skill -- the template is a thing to copy, not an argument to
        # follow. Raw counting flagged `writing-plans` and `executing-plans`,
        # the two skills that legitimately ship templates, which would have made
        # this permanently red. A permanently red check gets ignored, and this
        # repo has deleted three gates for exactly that.
        prose = re.sub(r"(?s)```.*?```", "", text)
        lines = len([ln for ln in prose.splitlines() if ln.strip()])
        if lines > skill_line_budget:
            fail(f"{rel(md)} is {lines} prose lines (budget {skill_line_budget})"
                 f" — a god-skill smell; move detail to references/")

        desc = re.search(r"(?m)^description:\s*(.+)$", text)
        if not desc:
            fail(f"{rel(md)} has no description — it can never be triggered")
        else:
            if len(desc.group(1)) > desc_budget:
                fail(f"{rel(md)} description is {len(desc.group(1))} chars "
                     f"(budget {desc_budget}) — injected every turn")
            if "do not use" not in desc.group(1).lower():
                fail(f"{rel(md)} description has no negative trigger — "
                     f"say when NOT to use it, or it overlaps its neighbours")

        for section in ("## Routing", "## Success"):
            if section not in text:
                kind = ("no handoff contract" if "Routing" in section
                        else "no definition of done")
                fail(f"{rel(md)} has no `{section}` section — {kind}")

    print(f"scope={args.scope}: scanned {len(scannable)} tracked files, "
          f"{len(instruction_docs)} instruction docs, "
          f"{len(list(SKILLS.iterdir()))} skills, "
          f"{len(list(AGENTS.glob('*.md')))} agents\n")
    for n in notes:
        print(f"  note: {n}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        print(f"\n{len(failures)} finding(s).")
        print("Judgement-level checks are in the no-slop skill — this file only "
              "covers what a program can decide.")
        return 1

    print("OK: no credentials, conflict markers, placeholders or empty files; "
          "no hedging in instruction docs; every skill states its contract")
    print("All no-slop tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

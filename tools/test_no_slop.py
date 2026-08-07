#!/usr/bin/env python3
"""Slop checks — the mechanically decidable subset, at two scopes.

    python tools/test_no_slop.py                 # --scope layer  (default)
    python tools/test_no_slop.py --scope repo    # everything git tracks

Why two scopes
--------------
The two cadences cost different amounts and answer different questions:

  layer   the `.claude/` capability layer only. Cheap. Runs as part of the
          normal suite every turn, and the drift counter named the
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


# --- portability -------------------------------------------------------------
#
# A skill is copied verbatim into another repository, so anything it asserts
# about THIS one becomes a false statement there. The lesson in "a hook that
# blocked a turn until a skill ran deadlocked and was deleted" is generic and
# worth keeping; "deleted on 2026-08-02" is provenance, and provenance does not
# travel. The same applies to counts and to sibling repo names.
#
# Opt-in, and deliberately not part of `layer` or `repo`: this repo carries
# years of hard-won specifics on purpose, and a check that turns the per-turn
# gate red on all of them gets switched off within a day. Run it before
# installing the layer somewhere, which is the only moment it matters.

DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
# Possessive ("this repo's base was master") and locative ("happened in this
# repo") are claims about ONE specific repository, and they are false anywhere
# else. Bare "this repo" is deixis -- "does this repo have a deploy target?" is
# true wherever it is read. Flagging six such sentences was this check's own
# false-positive rate, and a check that cries wolf gets switched off.
THIS_REPO_RE = re.compile(r"\bthis repo's\b|\bin this repo\b", re.IGNORECASE)
# Names of repositories this layer has lived in. A skill naming one is asserting
# something about a tree the reader may not have.
SIBLING_RE = re.compile(r"\b(?:physrun|UAIOS)\b")


def check_portability() -> int:
    """Is the layer safe to copy into a repository that is not this one?"""
    targets = sorted(list(SKILLS.rglob("*.md")) + list(AGENTS.rglob("*.md"))
                     + list((CLAUDE / "commands").rglob("*.md")))
    counts = {"dated claim": 0, "names this repo": 0, "names a sibling repo": 0}

    for path in targets:
        body = read_text(path)
        if body is None:
            continue
        for lineno, line in enumerate(body.splitlines(), 1):
            for label, rx in (("dated claim", DATE_RE),
                              ("names this repo", THIS_REPO_RE),
                              ("names a sibling repo", SIBLING_RE)):
                m = rx.search(line)
                if m:
                    counts[label] += 1
                    fail(f"{rel(path)}:{lineno} {label} ({m.group(0)!r}) — "
                         f"false in any other repository; keep the lesson, "
                         f"drop the provenance")

    print(f"scope=portability: read {len(targets)} skill, agent and command "
          f"files\n")
    if failures:
        for f in failures[:40]:
            print(f"FAIL: {f}")
        if len(failures) > 40:
            print(f"... and {len(failures) - 40} more")
        print("\n" + ", ".join(f"{v} {k}" for k, v in counts.items() if v))
        print(f"{len(failures)} finding(s). The layer will still FUNCTION "
              f"elsewhere — every one of these is a false statement, not a "
              f"broken mechanism.")
        return 1
    print("OK: nothing in the layer asserts anything about a specific repository")
    return 0


def check_temp_dir_cleanup() -> None:
    """No suite may let a temp-directory teardown decide its exit code.

    Git writes loose objects read-only; Windows refuses to delete read-only
    files; `TemporaryDirectory.__exit__` calls `shutil.rmtree` and raises. The
    failure lands AFTER every check has printed OK, so the suite exits non-zero
    with an output whose last line reads `OK: ...` -- a red build with no
    legible cause. It bit `test_session_start_contract.py` on 2026-08-07 and
    four more sites in `test_artifact_autocommit.py` were one `git commit` away
    from the same thing.

    `ignore_cleanup_errors=True` (Python 3.10+, CI runs 3.11) makes it
    impossible rather than unlikely. A leaked temp directory is the OS's
    problem; an unexplainable red suite is ours.
    """
    # Assembled at runtime, never written contiguously: this file is scanned by
    # the check it defines, and a literal here flags the guard itself. Same trap
    # the credential patterns hit on 2026-08-03, and it fired again here on the
    # first run of this check.
    needle = "TemporaryDirectory" + "("
    guard = "ignore_cleanup" + "_errors"
    for path in sorted(ROOT.glob("tools/*.py")) + sorted(
            (CLAUDE / "hooks").rglob("*.py")):
        text = read_text(path)
        if text is None:
            continue
        for num, line in enumerate(text.splitlines(), 1):
            if needle in line and guard not in line and "def " not in line:
                fail(f"{rel(path)}:{num} temp-dir context manager without "
                     f"{guard}=True — a git object left read-only makes "
                     f"teardown fail the suite after it has already passed")


def check_hook_spawn_stdin() -> None:
    """A test that spawns a hook must close or supply its stdin.

    `_hooklib.load_payload()` falls back to reading stdin, guarded only by
    `isatty()`. An inherited pipe is not a TTY, so the guard passes and the read
    blocks on an EOF that never arrives. A spawned hook inherits whatever the
    spawner had, and under `run_checks.py` -- itself launched from a pipe -- that
    is an open handle. The hook hangs, the suite dies on its timeout, and it only
    happens when run through the tier, never standalone.

    Proven 2026-08-07: same suite, `exit=124` with a pipe on stdin, `exit=0` with
    `< /dev/null`. `_hooklib` documents the trap for `run_hook.py`; the test had
    it too. Pass `stdin=subprocess.DEVNULL`, or set `HOOK_PAYLOAD` in the child's
    environment, which `load_payload` reads first for exactly this reason.
    """
    # Narrow on purpose. `sys.executable` is what distinguishes "spawns a Python
    # hook" from "runs git and happens to mention the hooks/state ledger path" --
    # the first draft of this check flagged resume.py and loop.py for the latter,
    # and a check that cries wolf is a check someone switches off.
    needle = "subprocess." + "run("
    for path in sorted(ROOT.glob("tools/*.py")):
        text = read_text(path)
        if text is None or needle not in text or "sys.executable" not in text:
            continue
        # Comments stripped first. The comment explaining WHY stdin must be
        # closed contains the string `stdin=`, so scanning raw text let a file
        # satisfy this check by talking about it -- caught on the first negative
        # test, which is the only reason it is not still true.
        code = "\n".join(ln for ln in text.splitlines()
                         if not ln.lstrip().startswith("#"))
        spawns_hook = "hooks" in code or "BOOTSTRAP_SCRIPT" in code
        if spawns_hook and "stdin=" not in code and "HOOK_PAYLOAD" not in code:
            fail(f"{rel(path)} spawns a hook without closing or supplying stdin — "
                 f"load_payload() blocks on an inherited pipe and the suite hangs "
                 f"only when run through the tier")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope", choices=("layer", "repo", "portability"),
                    default="layer",
                    help="layer = .claude/ only (default); repo = everything "
                         "tracked; portability = is the layer safe to install "
                         "into another repository")
    args = ap.parse_args()

    if args.scope == "portability":
        return check_portability()

    check_temp_dir_cleanup()
    check_hook_spawn_stdin()

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

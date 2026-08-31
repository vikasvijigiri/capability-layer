"""
SessionStart hook — global, runs once per session in every repo.

Scope, by design: repository detection, missing-scaffolding detection, and
minimal context loading. Nothing here authors strategic documents, writes
source, reviews, or commits — that's the model's job during the actual
session, not this deterministic script's.

Also subsumes the old inline "load HANDOFF.md" SessionStart command: this
script loads HANDOFF.md itself (plus a few other minimal-context sources),
so that logic isn't duplicated between two separate hook entries.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402




BOOTSTRAP_FILES = [
    "README.md",
    "CLAUDE.md",
    "TASK.md",
    "MEMORY.md",
    "HANDOFF.md",
    "LOG.md",
    "ISSUES.md",
]


def find_git_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, ".git")) or os.path.isfile(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def read_json_if_file(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# The authoring apparatus was deleted on 2026-08-09, not disabled: `detect_stack`,
# `detect_tooling`, `detect_commit_style`, `claude_md_skeleton`, nine `*_SKELETON`
# constants and `write_if_missing` -- 407 lines that no longer had a caller.
#
# This hook was changed from AUTHORING to DETECTION when the layer stopped
# installing itself into repositories unasked, and
# `tools/test_session_start_contract.py` asserts it creates nothing. The behaviour
# went; the code stayed, so the file read as though it still bootstrapped the
# knowledge docs. It does not. `knowledge-manager` owns README, TASK, MEMORY,
# HANDOFF, LOG, ISSUES and decisions/; `capability-layer-maintenance` owns
# CLAUDE.md. This hook only READS them and reports what it found.

def parse_active_tasks(task_md_path):
    if not os.path.isfile(task_md_path):
        return ""
    with open(task_md_path, encoding="utf-8") as f:
        text = f.read()
    match = re.search(r"(?ms)^## Active\s*\n(.*?)(?=^## Completed\b|\Z)", text)
    if match is None:
        return text  # older TASK.md without the Active/Completed split -- load as-is
    return match.group(1).strip()


def parse_active_task_pointers(task_md_path, max_status_chars=200):
    """Name + one-line status per active task -- not the full Goal/Input/
    Output/Constraints/Done Checks/Out of Scope detail, which stays a Read
    away instead of being paid on every SessionStart."""
    active_text = parse_active_tasks(task_md_path)
    if not active_text.strip():
        return ""
    pointers = []
    # Any heading depth, because `## Active` contains `###` tasks and splitting
    # on `## ` alone never split at all -- it returned the whole section as one
    # block whose "name" was the HTML comment at the top, and whose status was
    # therefore "(no Status field)". That is what this hook emitted on every
    # session until 2026-08-12: one useless line in place of every active task.
    for block in re.split(r"(?m)^#{2,4}\s+(?=\S)", active_text):
        block = block.strip()
        if not block or block.startswith("<!--"):
            continue
        name, _, rest = block.partition("\n")
        # Both `**Status**:` and `**Status:**` -- the format doc shows the first
        # and every TASK.md here writes the second, so accepting one of them is
        # how a field silently reads as absent.
        # Stop at the next bullet of ANY kind. Stopping only at a bold one let a
        # multi-line Status run on into `- Modify:` and `- Create:`, which are
        # plain bullets -- so the "one-line status" quietly became the whole
        # declaration block.
        status_match = re.search(
            r"(?ms)^-\s*\*\*Status:?\*\*:?\s*(.*?)(?=^\s*-\s|\Z)", rest)
        status = " ".join(status_match.group(1).split()) if status_match else "(no Status field)"
        if len(status) > max_status_chars:
            status = status[:max_status_chars].rstrip() + "..."
        pointers.append(f"- {name.strip()} -- Status: {status}")
    return "\n".join(pointers)


def parse_handoff_status(handoff_path):
    """Prefer the explicit <!-- session-context:start/end --> markers --
    robust against any future section added elsewhere in the file (a rogue
    section once rode along with a "Current Work onward" heuristic; a tagged
    boundary can't be fooled that way). Falls back to that same "Current Work
    onward" heuristic for older HANDOFF.md files written before the marker
    convention existed."""
    if not os.path.isfile(handoff_path):
        return ""
    with open(handoff_path, encoding="utf-8") as f:
        text = f.read()
    tagged = re.search(
        r"(?ms)^<!--\s*session-context:start\s*-->\s*\n(.*?)\n^<!--\s*session-context:end\s*-->",
        text,
    )
    if tagged is not None:
        return _clip(tagged.group(1).strip(), HANDOFF_BUDGET, "HANDOFF.md")
    match = re.search(r"(?ms)^## Current Work\s*\n.*\Z", text)
    if match is None:
        # Older/unrecognised format. Falling back to the whole file is right --
        # something is better than nothing -- but it must still be budgeted, or
        # an unmarked HANDOFF.md injects itself entirely.
        return _clip(text, HANDOFF_BUDGET, "HANDOFF.md")
    return _clip(match.group(0).strip(), HANDOFF_BUDGET, "HANDOFF.md")


# Character budgets for what this hook injects at session start.
#
# Measured 2026-08-02: the payload was 26,990 chars (~6,750 tokens) spent before
# the user had typed anything, because both parsers below were uncapped -- five
# whole LOG entries plus everything in HANDOFF.md from "Current Work" onward.
# Long entries are good writing and bad context; the fix is a budget here, not
# shorter entries.
#
# Truncation always names the file, so the full text stays one Read away. An
# injected summary is a pointer, never a replacement.
# Halved again on 2026-08-12, from 2400/2400/3, after `tools/bench.py` put a
# number on what remained: 6,258 chars (~1,560 tokens) still spent before the
# user types. The 2026-08-02 cut fixed the catastrophe and left the habit.
#
# What a session opening actually needs is *where it is*, not *what happened*.
# HANDOFF's first paragraph is the START HERE line and earns its place; the
# Pending list behind it does not, because nothing in it is actionable until
# something is chosen. One LOG entry says what the last unit was; the second and
# third are history, and history is what `LOG.md` is for. Every clip names its
# file, so nothing here is lost -- it is one Read away instead of always paid.
HANDOFF_BUDGET = 1000
LOG_ENTRY_BUDGET = 500
LOG_TOTAL_BUDGET = 500
LOG_ENTRIES = 1


def _clip(text, budget, what):
    if len(text) <= budget:
        return text
    return text[:budget].rstrip() + f"\n[... clipped, Read {what} for the rest]"


def parse_last_n_log_entries(log_path, n=LOG_ENTRIES):
    if not os.path.isfile(log_path):
        return ""
    with open(log_path, encoding="utf-8") as f:
        text = f.read()
    parts = re.split(r"(?m)^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}.*)$", text)
    entries = []
    i = 1
    while i < len(parts) - 1:
        entries.append(_clip(parts[i] + parts[i + 1], LOG_ENTRY_BUDGET, "LOG.md"))
        i += 2
    return _clip("".join(entries[:n]), LOG_TOTAL_BUDGET, "LOG.md")


def _parse_env_file(path):
    """Return {key: value} for non-comment lines. Values are never logged
    or surfaced anywhere -- only key names and whether a value is blank."""
    values: dict[str, str] = {}
    if not os.path.isfile(path):
        return values
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def check_env_setup(root):
    """If .env.example exists, report which of its (non-optional, i.e. not
    commented-out) keys are missing or still blank in .env. Never reads or
    reports actual secret values -- key names only."""
    example_path = os.path.join(root, ".env.example")
    if not os.path.isfile(example_path):
        return []
    example_keys = _parse_env_file(example_path)
    actual = _parse_env_file(os.path.join(root, ".env"))
    return [key for key in example_keys if not actual.get(key)]


def is_stub_claude_md(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            return "Auto-bootstrapped stub" in f.read()
    except Exception:
        return False


def list_decisions(root):
    decisions_dir = os.path.join(root, "decisions")
    if not os.path.isdir(decisions_dir):
        return []
    return sorted(
        name for name in os.listdir(decisions_dir)
        if name.endswith(".md") and name != "README.md"
    )


def main():
    # Consume the standard Claude Code payload even though this hook's current
    # policy is identical for startup, resume, and compact events.
    load_payload()
    root = find_git_root(os.getcwd())
    if root is None:
        return

    missing_docs = [
        name for name in BOOTSTRAP_FILES
        if not os.path.isfile(os.path.join(root, name))
    ]
    missing_dirs = [
        name for name in ("decisions", "docs", "docs/plans", "docs/archive")
        if not os.path.isdir(os.path.join(root, name))
    ]

    missing_env_keys = check_env_setup(root)

    sections = []
    if missing_env_keys:
        sections.append(
            "--- Setup checklist ---\n"
            "This repo has a .env.example with keys not yet set in .env: "
            + ", ".join(missing_env_keys)
            + ". Remind the user at a convenient point (not necessarily now) -- "
            "never fill these in yourself, they're the user's own credentials."
        )
    if missing_docs or missing_dirs:
        sections.append(
            "--- Documentation drift detected (read-only) ---\n"
            f"Missing strategic documents: {', '.join(missing_docs) or 'none'}. "
            f"Missing directories: {', '.join(missing_dirs) or 'none'}. "
            "Route the repair to the documented owner; this hook never writes "
            "strategic content."
        )

    claude_md_path = os.path.join(root, "CLAUDE.md")
    if is_stub_claude_md(claude_md_path):
        sections.append(
            "--- CLAUDE.md is still a stub ---\n"
            "CLAUDE.md hasn't been filled in yet (still the "
            "auto-generated skeleton). Once there's enough context about the repository, fill it in with "
            "real project specifics — commands, layout, gotchas, and hard rules."
        )
    # Full CLAUDE.md content is deliberately NOT injected here -- Claude Code
    # already auto-loads project CLAUDE.md on its own for every session, so
    # re-reading and re-printing it here would just duplicate that context.

    active_pointers = parse_active_task_pointers(os.path.join(root, "TASK.md"))
    if active_pointers:
        sections.append(
            "--- TASK.md (Active -- name + status only; Read the file for "
            "full Goal/Input/Output/Constraints/Done Checks/Out of Scope "
            "detail) ---\n" + active_pointers
        )

    handoff_path = os.path.join(root, "HANDOFF.md")
    handoff_status = parse_handoff_status(handoff_path)
    if handoff_status.strip():
        sections.append(
            "--- HANDOFF.md (Current Work / Pending / Next Steps / Open "
            "Questions -- Read the file for the full Completed history) ---\n"
            + handoff_status
        )

    # No explicit n: the budget lives with the parser, next to the other three
    # constants. Passing n=5 here silently overrode LOG_ENTRIES and shipped four
    # entries under a header claiming five -- caught by running the hook.
    last_logs = parse_last_n_log_entries(os.path.join(root, "LOG.md"))
    if last_logs.strip():
        sections.append(
            f"--- LOG.md (last {LOG_ENTRIES} entries, clipped) ---\n" + last_logs)

    decision_files = list_decisions(root)
    if decision_files:
        sections.append(
            "--- decisions/ (filenames only, read on demand if relevant) ---\n"
            + "\n".join(decision_files)
        )

    if sections:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n\n".join(sections),
            }
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

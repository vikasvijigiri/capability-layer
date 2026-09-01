"""
SessionStart hook — global, runs once per session in every repo.

Scope, by design: repository detection, missing-scaffolding detection, and
minimal context loading. Nothing here authors strategic documents, writes
source, reviews, or commits — that's the model's job during the actual
session, not this deterministic script's.

Context loading is bounded by design: each knowledge doc has a delimited
"head" region — `<!-- session-context:start -->` … `<!-- session-context:end -->`
for TASK.md and HANDOFF.md, the single newest dated entry for LOG.md — which
this hook emits VERBATIM. It never reads a whole file and never clips
mid-line: a head over its ceiling is cut at a newline with a pointer, and a
well-formed head never reaches the ceiling. See
`decisions/2026-09-01-knowledge-doc-head-contract.md`.
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

# Character ceilings for the injected head of each doc. Generous on purpose:
# each doc's SCHEMA keeps its head small — TASK.md is <=6 one-row entries,
# HANDOFF.md is three short sections, and LOG.md's newest entry is capped at
# 20 lines by tools/test_doc_entries.py — so a head that hits one of these is
# a writing-discipline problem the pointer surfaces, not something to design
# around. `_emit_head` only ever cuts at a newline.
TASK_HEAD_CEILING = 1200
HANDOFF_HEAD_CEILING = 1600
LOG_HEAD_CEILING = 1400

SESSION_CONTEXT_RE = re.compile(
    r"(?ms)^<!--\s*session-context:start\s*-->\s*\n(.*?)\n^<!--\s*session-context:end\s*-->"
)


def find_git_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, ".git")) or os.path.isfile(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


# The authoring apparatus was deleted on 2026-08-09, not disabled: `detect_stack`,
# `detect_tooling`, `detect_commit_style`, `claude_md_skeleton`, nine `*_SKELETON`
# constants and `write_if_missing` -- 407 lines that no longer had a caller.
#
# This hook was changed from AUTHORING to DETECTION when the layer stopped
# installing itself into repositories unasked, and
# `tools/test_session_start_contract.py` asserts it creates nothing.
# `documentation` owns README, TASK, MEMORY, HANDOFF, LOG, ISSUES and
# decisions/; `capability-layer-maintenance` owns CLAUDE.md. This hook only
# READS a bounded head of each and reports what it found.


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _emit_head(text, ceiling, what):
    """Emit `text` whole, or -- only if it exceeds `ceiling` -- cut at the
    last newline before the ceiling and append a pointer. Never splits a
    line. Truncation always names the file, so the full text stays one Read
    away; an injected head is a pointer, never a replacement."""
    text = text.strip()
    if len(text) <= ceiling:
        return text
    cut = text.rfind("\n", 0, ceiling)
    if cut <= 0:
        cut = ceiling
    return text[:cut].rstrip() + f"\n[... head over budget, Read {what} for the rest]"


def _marked_region(text):
    """The text between <!-- session-context:start --> and :end, or None.

    An explicit tagged boundary can't be fooled by a section added elsewhere
    in the file -- a rogue section once rode along with a looser "from this
    heading onward" heuristic."""
    match = SESSION_CONTEXT_RE.search(text)
    return match.group(1).strip() if match is not None else None


def parse_task_head(task_md_path):
    """TASK.md's delimited head region, verbatim. Falls back to the `## Active`
    section for an un-migrated TASK.md that predates the markers -- bounded
    either way."""
    if not os.path.isfile(task_md_path):
        return ""
    text = _read(task_md_path)
    region = _marked_region(text)
    if region is not None:
        return _emit_head(region, TASK_HEAD_CEILING, "TASK.md")
    match = re.search(r"(?ms)^## Active\s*\n(.*?)(?=^## Completed\b|\Z)", text)
    active = (match.group(1) if match else text).strip()
    return _emit_head(active, TASK_HEAD_CEILING, "TASK.md") if active else ""


def parse_handoff_head(handoff_path):
    """HANDOFF.md's delimited head region, verbatim. Falls back to
    `## Resume here` / `## Current Work` onward for an un-migrated file, then
    to the whole file -- all three bounded."""
    if not os.path.isfile(handoff_path):
        return ""
    text = _read(handoff_path)
    region = _marked_region(text)
    if region is not None:
        return _emit_head(region, HANDOFF_HEAD_CEILING, "HANDOFF.md")
    match = re.search(r"(?ms)^## (?:Resume here|Current Work)\b.*\Z", text)
    fallback = (match.group(0) if match else text).strip()
    return _emit_head(fallback, HANDOFF_HEAD_CEILING, "HANDOFF.md") if fallback else ""


def parse_latest_log_entry(log_path):
    """The single newest dated LOG.md entry, verbatim (bounded). What a
    session opening needs is a pointer to the last unit of work; earlier
    entries are history, which is what the rest of LOG.md is for."""
    if not os.path.isfile(log_path):
        return ""
    text = _read(log_path)
    parts = re.split(r"(?m)^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}.*)$", text)
    if len(parts) < 3:
        return ""
    return _emit_head(parts[1] + parts[2], LOG_HEAD_CEILING, "LOG.md")


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

    task_head = parse_task_head(os.path.join(root, "TASK.md"))
    if task_head:
        sections.append("--- TASK.md (live ledger) ---\n" + task_head)

    handoff_head = parse_handoff_head(os.path.join(root, "HANDOFF.md"))
    if handoff_head:
        sections.append("--- HANDOFF.md (resume here) ---\n" + handoff_head)

    latest_log = parse_latest_log_entry(os.path.join(root, "LOG.md"))
    if latest_log:
        sections.append("--- LOG.md (newest entry) ---\n" + latest_log)

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

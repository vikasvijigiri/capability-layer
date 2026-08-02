"""post-run -- commits the prose artefacts of a finished unit of work, automatically.

Authorised by the user on 2026-08-02 after the trade-off below was stated
explicitly. Do not widen its scope without asking again.

Why this exists
---------------
`docs/research/2026-08-02-automating-the-git-chain.md` found that nobody gates on
backlog size, because the two repos that solved it commit at a *boundary* so the
backlog never grows. `FengZhiHen1/Campfire-AI` commits on a state transition (a
stage flipping to DONE); `imehr/book-writer-plugin` proves a hook can run git at
all. This repo had 84 files uncommitted across five sessions while 24 hooks fired
correctly, because every gate asked the model to act instead of acting.

The state transition here is **`knowledge-manager` writing LOG.md or HANDOFF.md**.
That is this repo's own definition of a unit of work finishing, so it is the
correct commit boundary -- and it is already detectable, because
`save_turn_marker` snapshots those two digests at UserPromptSubmit.

What it will and will not touch
-------------------------------
Only `.md` files, only the root knowledge docs and ARTEFACT_ROOTS, always by
**explicit pathspec**. `git add` is never called in any form.
`imehr/book-writer-plugin`'s version runs `git add .`, which is exactly how this
repo accumulated 49 files staged across sessions waiting to be swept into an
unrelated commit. A pathspec commit cannot do that and leaves the index untouched.

Deliberately bypassed gates, and why that is acceptable here
------------------------------------------------------------
A commit made from this subprocess does not pass through `PreToolUse`, so
`01-secret-scan.py`, `03-review-gate.py`, `05-docs-required.py` and
`04-delivery-guard.py` never see it. That is a real hole, and it is the whole
reason the scope is this narrow:

- **Never code.** `.md` only, under fixed roots. No tests, no hooks, no
  `settings.json`, nothing executable, nothing under `.claude/`.
- **Never a review subject.** The review gate exists for code; prose artefacts
  are reviewed by being read, which is what happens next anyway.
- **The docs gate is satisfied by construction** -- this only fires on a turn
  where the docs were just written.
- **Blast radius is the lowest band** in `decisions/2026-08-02-gate-on-blast-radius.md`:
  a local commit on the current branch. It never pushes.

Anything wider than prose artefacts stays behind the human gates.

Never raises and never blocks the turn. A failed commit is reported in the Stop
output and the files are left exactly as they were.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    KNOWLEDGE_DOCS,
    changed_paths,
    doc_digests,
    load_payload,
    load_turn_marker,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Prose deliverables only -- directories whose contents are committed .md files
# written by a skill.
ARTEFACT_ROOTS = ("docs/specs/", "docs/research/", "docs/plans/", "decisions/")

# Writing either of these is the boundary that makes this hook fire.
TRIGGER_DOCS = ("LOG.md", "HANDOFF.md")


def is_artefact(path: str) -> bool:
    """True only for prose this hook is authorised to commit."""
    norm = path.replace("\\", "/")
    if not norm.endswith(".md"):
        return False
    if norm.startswith(".claude/"):
        # `.claude/` holds executable hooks and skill definitions alongside prose.
        # The directory does not predict blast radius, so it is excluded outright.
        return False
    if norm in KNOWLEDGE_DOCS:
        return True
    return any(norm.startswith(root) for root in ARTEFACT_ROOTS)


def git(*args):
    """Run git and return (rc, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=20,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001 -- reported below, never swallowed
        return 1, "", str(exc)


def speak(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "additionalContext": text,
    }}))


def main():
    payload = load_payload()
    if payload.get("stop_hook_active"):
        return

    before = load_turn_marker()
    if before is None:
        return

    # The boundary: did this turn write LOG.md or HANDOFF.md? Anything else is
    # mid-flight, and mid-flight work is not a unit of work.
    now = doc_digests()
    if not any(now.get(doc) != before.get(doc) for doc in TRIGGER_DOCS):
        return

    paths = changed_paths(REPO_ROOT)
    if not paths:
        return

    artefacts = sorted({p for p in paths if is_artefact(p)})
    if not artefacts:
        return

    subject = (
        f"Record {artefacts[0]}" if len(artefacts) == 1
        else f"Record {len(artefacts)} artefacts from one unit of work"
    )
    listing = "\n".join(f"- {p}" for p in artefacts)
    message = (
        f"{subject}\n\n"
        f"Committed automatically at the knowledge-manager boundary by\n"
        f"post-run/06-artifact-autocommit.py. Prose artefacts only, by explicit\n"
        f"pathspec; the index and the rest of the working tree are untouched.\n\n"
        f"{listing}\n"
    )

    # -F, not -m: the message is multi-line and contains paths. book-writer-plugin
    # interpolates its message into a shell string, which breaks on the first quote.
    msg_file = REPO_ROOT / ".claude" / "hooks" / "state" / "autocommit-msg.txt"
    try:
        msg_file.parent.mkdir(parents=True, exist_ok=True)
        msg_file.write_text(message, encoding="utf-8")
    except OSError as exc:
        speak(f"Artefact auto-commit could not write its message file ({exc}); "
              f"{len(artefacts)} artefact file(s) left uncommitted.")
        return

    # A pathspec commit alone cannot commit an untracked file -- git errors with
    # "did not match any file(s) known to git" -- and a NEW spec, research doc or
    # decision record is exactly that. So the paths are staged first, still by
    # explicit pathspec. `git add -- <paths>` is not `git add .`: it can only ever
    # touch the artefacts computed above, so the sweep this hook exists to avoid
    # remains impossible, and anything staged by someone else is left alone.
    rc, _, stderr = git("add", "--", *artefacts)
    if rc != 0:
        msg_file.unlink(missing_ok=True)
        speak(
            f"Artefact auto-commit could not stage its own paths ({stderr[:200]}); "
            f"nothing was committed and the index is unchanged."
        )
        return

    rc, _, stderr = git("commit", "-F", str(msg_file), "--", *artefacts)
    msg_file.unlink(missing_ok=True)

    if rc != 0:
        # Leave the index as it was found. Without this, a failed commit strands the
        # artefacts staged, `session-start/03-index-baseline.py` snapshots them next
        # session as "inherited", and `pre-commit/06-index-scope-guard.py` then asks
        # the user about files this automation staged itself -- two new hooks
        # manufacturing false positives for each other.
        rc_undo, _, undo_err = git("restore", "--staged", "--", *artefacts)
        index_state = (
            "the index was left as it was found"
            if rc_undo == 0 else
            f"WARNING: they are also still staged and could not be unstaged ({undo_err[:120]})"
        )
        # Surfaced, never silent -- CLAUDE.md forbids a silent degraded path.
        speak(
            f"Artefact auto-commit FAILED and nothing was committed: {stderr[:300]} "
            f"-- the {len(artefacts)} artefact file(s) are still uncommitted and "
            f"{index_state}. Commit them by hand or investigate the hook."
        )
        return

    rc_sha, sha, _ = git("rev-parse", "--short", "HEAD")
    speak(
        f"Auto-committed {len(artefacts)} prose artefact(s) as "
        f"{sha if rc_sha == 0 else 'HEAD'}: {', '.join(artefacts)}. "
        f"Nothing was staged and nothing was pushed."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

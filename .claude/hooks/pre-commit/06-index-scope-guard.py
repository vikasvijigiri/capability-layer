"""pre-commit -- guards the staging area, the one step in the chain with no gate.

The hole this closes
--------------------
`git add` was completely unguarded, and a commit spends whatever the index happens
to hold. Those two facts together produced the concrete failure on 2026-08-02: 50
files staged in earlier sessions (48 `docs/archive/` renames plus
`.claude/workflow.md`) sat in the index for days, and every commit attempted after
them would have carried them along under an unrelated message. The same shape is
in `imehr/book-writer-plugin`, which runs `git add .` from a hook -- see
`docs/research/2026-08-02-automating-the-git-chain.md`.

Two triggers, because the accumulation and the harm happen at different moments:

  1. **A blanket `git add`** (`.`, `-A`, `--all`, `:/`) is how the index silently
     grows to include things nobody chose. Caught at the moment of growth.
  2. **A commit carrying files staged before this session started** is the actual
     harm -- somebody else's work, in your commit, under your message. Caught at the
     moment it would be spent.

Trigger 2 is the load-bearing one. Staging a file hurts nobody; committing it does.

`ask`, never `deny`
-------------------
Both cases are legitimate operations with a correct way to proceed -- sometimes you
really do mean `git add -A`, and sometimes the inherited files are exactly what you
intend to commit. `deny` would be wrong and would be worked around. This asks once,
with the count and the paths, so the answer is informed rather than reflexive.
`02-branch-guard.py` documents the opposite choice for its own case, and the
difference is whether a correct alternative exists.

Fails open everywhere. No baseline, no git, no repo -> silent. A guard that cannot
read git state must never be able to wedge the repo.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import ask, command_of, load_index_baseline, load_payload, staged_paths  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

COMMIT_RE = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*commit\b")
DRY_RUN_RE = re.compile(r"--dry-run\b")

# `git add` with a pathspec that means "whatever is lying around" rather than a
# named file. `-u`/`--update` is deliberately NOT here: it only restages files git
# already tracks changes for, which is a much narrower act than -A.
# Non-greedy `\S+` between `git` and `add` so global flags that take a value are
# covered -- `git -C /repo add .` is two tokens before the subcommand, which a
# `-\S+` repetition misses. `\badd\b` cannot match `--all` or `--amend`, so the
# looseness costs little.
ADD_RE = re.compile(r"\bgit\s+(?:\S+\s+)*?add\b")

# Matching a verb anywhere in the string, including inside quotes, is this repo's
# settled position for an `ask` -- see decisions/2026-08-01-review-gate-matches-
# verbs-anywhere.md. One extra prompt is cheaper than a missed sweep, and the ADR
# is explicit that this reasoning holds for `ask` and NOT for `deny`.
BLANKET_RE = re.compile(r"""
    (?:^|\s)
    (?: -A\b | --all\b | --no-ignore-removal\b   # explicit all-flags
      | \.(?=[\s'"]|$)                            # a bare . -- may close a quote
      | :/(?=[\s'"]|$)                            # the repo-root magic pathspec
      | \*(?=[\s'"]|$)                            # a bare glob
    )
""", re.VERBOSE)

# A commit naming its own paths (`git commit -- a.md b.md`) cannot sweep: git only
# takes the paths listed. `post-run/06-artifact-autocommit.py` relies on this.
PATHSPEC_COMMIT_RE = re.compile(r"\bcommit\b.*\s--\s+\S")

MAX_LISTED = 8


def summarise(paths):
    shown = ", ".join(paths[:MAX_LISTED])
    if len(paths) > MAX_LISTED:
        shown += f", and {len(paths) - MAX_LISTED} more"
    return shown


def main():
    payload = load_payload()
    command = command_of(payload)
    if not command:
        return

    if os.environ.get("ALLOW_WIDE_STAGE") == "1":
        return

    # The command may target a different repo or a subdirectory, so read the index
    # git would actually read. `02-branch-guard.py` established this pattern; using
    # REPO_ROOT unconditionally reported the wrong index for any such command.
    cwd = payload.get("cwd") or REPO_ROOT

    # --- trigger 1: a blanket add
    if ADD_RE.search(command) and BLANKET_RE.search(command):
        current = staged_paths(cwd)
        already = f" The index already holds {len(current)} file(s)." if current else ""
        ask(
            f"index-scope-guard: `{command.strip()[:120]}` stages everything in the "
            f"working tree, not a set you chose.{already} This is how 50 files from "
            f"earlier sessions ended up staged in this repo for days.\n\n"
            f"Prefer naming the paths:\n\n    git add -- path/one path/two\n\n"
            f"Proceed only if you do mean everything. ALLOW_WIDE_STAGE=1 skips this "
            f"check for one command."
        )
        return

    # --- trigger 2: a commit that would spend files this session never staged
    if not COMMIT_RE.search(command) or DRY_RUN_RE.search(command):
        return
    if PATHSPEC_COMMIT_RE.search(command):
        return  # names its own paths; cannot sweep

    baseline = load_index_baseline()
    if baseline is None:
        return  # never found out what was inherited -- cannot judge
    if not baseline:
        return  # the index was clean at session start; everything staged is ours

    current = staged_paths(cwd)
    if not current:
        return

    inherited = sorted(set(baseline) & set(current))
    if not inherited:
        return  # the inherited files were dealt with already

    mine = len(current) - len(inherited)
    ask(
        f"index-scope-guard: this commit would include {len(inherited)} file(s) that "
        f"were already staged when this session began, alongside {mine} from this "
        f"session.\n\nInherited: {summarise(inherited)}\n\n"
        f"They belong to earlier work and would land under this commit's message. "
        f"Either commit only what you meant:\n\n"
        f"    git commit -F <msg> -- <the paths for this change>\n\n"
        f"or unstage the inherited set first:\n\n"
        f"    git restore --staged -- {inherited[0]} …\n\n"
        f"Proceed only if they genuinely belong in this commit. ALLOW_WIDE_STAGE=1 "
        f"skips this check for one command."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

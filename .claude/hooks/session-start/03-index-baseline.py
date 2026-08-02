"""session-start -- records which files were already staged when this session began.

Staging is the only step in the edit -> commit -> push chain with no guard on it.
On 2026-08-02 this repo had 50 files staged from earlier sessions -- 48 archive
renames plus `.claude/workflow.md` -- sitting in the index for days. Any commit
made in a later session would have swept them in under an unrelated message, and
`docs/research/2026-08-02-automating-the-git-chain.md` found the same failure in
`imehr/book-writer-plugin`, which runs `git add .` from a hook.

Git itself cannot tell "I staged this a moment ago" from "someone staged this on
Tuesday": the index records paths, not when they arrived. So the set is snapshotted
once here, and `pre-commit/06-index-scope-guard.py` treats anything still in it at
commit time as a file the current session never chose.

Writes state and says nothing. A session start that produced output every time
would train the user to skip reading it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import save_index_baseline  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]


def main():
    save_index_baseline(REPO_ROOT)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

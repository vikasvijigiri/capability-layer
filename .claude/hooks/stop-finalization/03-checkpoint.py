"""stop-finalization -- writes a recoverable snapshot of the working tree at turn end.

The safety net: if work is lost, overwritten or a change goes wrong, every turn
boundary is recoverable. Local only -- it never pushes, never creates a branch
you might switch to by accident, and never appears in `git log`.

How it avoids touching anything
-------------------------------
A checkpoint is built in a THROWAWAY INDEX (GIT_INDEX_FILE points at a temp
file), so the real index, the working tree and HEAD are never read-modified.
The resulting commit is stored under `refs/checkpoints/<timestamp>`, outside
`refs/heads/`, so it is not a branch and does not show up in normal history.

Deliberately not `git stash create`: that ignores untracked files, so in a fresh
or partially-tracked repo it would cheerfully snapshot nothing at all while
appearing to work.

Recovering a checkpoint
-----------------------
    git log --oneline refs/checkpoints/          # what snapshots exist
    git show <ref>                               # what changed in one
    git restore --source=<ref> -- <path>         # pull one file back
    git checkout -b rescue <ref>                 # get all of it back

Retention: the newest MAX_CHECKPOINTS are kept, older refs are deleted. Nothing
is ever garbage-collected out from under an existing ref, so a kept checkpoint
stays recoverable indefinitely.

Fails open and silent. A snapshot that cannot be taken must never break a turn.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

CHECKPOINT_NS = "refs/checkpoints"
MAX_CHECKPOINTS = 50
TIMEOUT = 30


def git(args, cwd, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        timeout=TIMEOUT, shell=False, env=full_env,
    )


def prune(root):
    """Delete all but the newest MAX_CHECKPOINTS refs."""
    listed = git(["for-each-ref", "--format=%(refname)", "--sort=-refname",
                  CHECKPOINT_NS], root)
    if listed.returncode != 0:
        return 0
    refs = [r for r in listed.stdout.splitlines() if r.strip()]
    removed = 0
    for ref in refs[MAX_CHECKPOINTS:]:
        if git(["update-ref", "-d", ref], root).returncode == 0:
            removed += 1
    return removed


def main():
    payload = load_payload()
    # Stop hooks can be re-entered while the runtime is continuing a stop
    # decision. Never create a second checkpoint during that continuation.
    if payload.get("stop_hook_active"):
        return
    cwd = payload.get("cwd") or os.getcwd()

    root_proc = git(["rev-parse", "--show-toplevel"], cwd)
    if root_proc.returncode != 0:
        return  # not a repo
    root = root_proc.stdout.strip()

    # No commits yet -> no parent to hang a checkpoint off. Skip rather than
    # invent a root commit, which would put objects in a repo the user has not
    # yet chosen to populate.
    if git(["rev-parse", "--verify", "HEAD"], root).returncode != 0:
        return

    tmp_index = tempfile.NamedTemporaryFile(prefix="ckpt-index-", delete=False)
    tmp_index.close()
    os.unlink(tmp_index.name)  # git wants the path free, not an empty file
    env = {"GIT_INDEX_FILE": tmp_index.name}

    try:
        if git(["read-tree", "HEAD"], root, env).returncode != 0:
            return
        if git(["add", "-A"], root, env).returncode != 0:
            return

        tree_proc = git(["write-tree"], root, env)
        if tree_proc.returncode != 0:
            return
        tree = tree_proc.stdout.strip()

        head_tree = git(["rev-parse", "HEAD^{tree}"], root).stdout.strip()
        if tree == head_tree:
            return  # nothing changed since HEAD; no snapshot worth keeping

        stamp = time.strftime("%Y%m%d-%H%M%S")
        commit_proc = git(
            ["commit-tree", tree, "-p", "HEAD", "-m", f"checkpoint {stamp}"], root
        )
        if commit_proc.returncode != 0:
            return
        commit = commit_proc.stdout.strip()

        ref = f"{CHECKPOINT_NS}/{stamp}"
        if git(["update-ref", ref, commit], root).returncode != 0:
            return

        # The checkpoint ref IS the record -- `git for-each-ref` under
        # CHECKPOINT_NS lists every one, with its commit and its time. A parallel
        # `checkpoint.log` restated that less reliably and nothing read it.
        prune(root)
    finally:
        try:
            os.unlink(tmp_index.name)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

"""permission-security -- refuses a commit that would put AI attribution in git history.

Dispatched on Bash|PowerShell. Denies; never rewrites the command, because a
check silently editing a commit message is worse than one that refuses and
says why.

Why this exists when a setting already covers it
------------------------------------------------
`~/.claude/settings.json` sets `attribution.commit` and `attribution.pr` to ""
and `attribution.sessionUrl` to false, which stops Claude Code appending
anything of its own. That is the right layer and it handles the common case.

It does not handle a message typed by hand. `_hooklib.AI_ATTRIBUTION_PATTERNS`
is checked by `stop-finalization/06-artifact-autocommit.py` over messages it
generates ITSELF -- CLAUDE.md states the consequence outright: "Yours are
unchecked." A `git commit -m "... Co-Authored-By: Claude"` written directly
reached history with nothing looking. This is the thing that looks.

Two things are checked, both cheap
----------------------------------
1. **The message**, taken from `-m/--message` on the command line. The same
   patterns the auto-commit uses, so the two cannot disagree.
2. **The resolved author for the target repo.** A `user.name` or `user.email`
   configured to an AI puts the wrong name on every commit, and no
   per-message check would ever see it. Read from the command's actual
   target repo, not the session's.

Fails open: any error means no opinion and the commit proceeds.

Moved from `pre-commit/03-attribution-guard.py` on 2026-08-21, refactored
into a `check(payload) -> str | None` function so `00-dispatch.py` can call
it in-process alongside its three siblings. Behavior unchanged.
"""

import re

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    AI_ATTRIBUTION_PATTERNS,
    command_of,
    git_target_dir,
    is_git_commit,
    load_payload,
)

MSG_RE = re.compile(
    r"""(?:^|\s)(?:-m|--message)(?:\s+|=)(?:"([^"]*)"|'([^']*)'|(\S+))""")

FILE_RE = re.compile(
    r"""(?:^|\s)(?:-F|--file)(?:\s+|=)(?:"([^"]*)"|'([^']*)'|(\S+))""")


def messages(cmd: str) -> list[str]:
    """Every commit message the command supplies, however it supplies it."""
    out: list[str] = []
    for m in MSG_RE.finditer(cmd):
        value = next((g for g in m.groups() if g is not None), "")
        if value:
            out.append(value)
    for m in FILE_RE.finditer(cmd):
        value = next((g for g in m.groups() if g is not None), "")
        if not value:
            continue
        try:
            out.append(Path(value).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    return out


def target_dir(cmd: str) -> str:
    return git_target_dir(cmd, ".")


def configured_author(cwd: str) -> str:
    try:
        p = subprocess.run(["git", "config", "--get-regexp", r"^user\.(name|email)$"],
                           cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def first_hit(text: str) -> str:
    for pattern in AI_ATTRIBUTION_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0)
    return ""


def check(payload: dict) -> str | None:
    """The deny reason if this commit carries AI attribution, else None."""
    cmd = command_of(payload)
    if not cmd or not is_git_commit(cmd):
        return None

    for msg in messages(cmd):
        found = first_hit(msg)
        if found:
            return (
                f"This commit message carries AI attribution ({found!r}). "
                f"Git history is permanent and CLAUDE.md forbids it outright. "
                f"Remove that line and commit again -- the message is yours to "
                f"write, so this check refuses rather than editing it."
            )

    author = configured_author(target_dir(cmd))
    found = first_hit(author)
    if found:
        return (
            f"`user.name`/`user.email` in the target repo resolves to {found!r}, "
            f"so every commit there would carry the wrong author. Fix it with "
            f"`git config user.name` and `git config user.email` before "
            f"committing. No per-message check would have caught this."
        )
    return None


if __name__ == "__main__":
    from _hooklib import deny  # noqa: E402
    try:
        reason = check(load_payload())
        if reason:
            deny(reason)
    except Exception:
        pass

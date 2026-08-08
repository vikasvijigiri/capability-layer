"""pre-commit -- refuses a commit that would put AI attribution in git history.

PreToolUse on Bash|PowerShell. DENIES; it never rewrites the command, because a
hook silently editing a commit message is worse than one that refuses and says
why.

Why this exists when a setting already covers it
------------------------------------------------
`~/.claude/settings.json` sets `attribution.commit` and `attribution.pr` to `""`
and `attribution.sessionUrl` to false, which stops Claude Code appending anything
of its own. That is the right layer and it handles the common case.

It does not handle a message typed by hand. `_hooklib.AI_ATTRIBUTION_PATTERNS` is
checked by `post-run/06-artifact-autocommit.py` over messages it generates
ITSELF -- CLAUDE.md states the consequence outright: "Yours are unchecked." A
`git commit -m "... Co-Authored-By: Claude"` written directly reached history with
nothing looking. This is the thing that looks.

`04-delivery-guard.py` covered part of this and was deleted on 2026-08-02 in the
hook prune. It went because it also did four other things; the attribution check
was the half worth keeping.

Two things are checked, both cheap
----------------------------------
1. **The message**, taken from `-m/--message` on the command line. The same
   patterns the auto-commit uses, so the two cannot disagree.
2. **The resolved author for the target repo.** A `user.name` or `user.email`
   configured to an AI puts the wrong name on every commit, and no per-message
   check would ever see it. Read from the command's actual target repo, not the
   session's -- `git -C ../other commit` commits somewhere else, which is the bug
   `02-branch-guard.py` was fixed for on 2026-08-03.

Fails open: any error means no opinion and the commit proceeds. A guard that
wedges the session on its own bug is worse than the attribution it prevents.
"""

import re

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    AI_ATTRIBUTION_PATTERNS,
    command_of,
    deny,
    git_target_dir,
    is_git_commit,
    load_payload,
)

# Message values, both spellings and both quote styles, in one pass.
#
# `shlex.split(cmd, posix=False)` was tried first and is wrong here: it does not
# group a quoted span, so `--message="feat: y"` came back as the token
# `--message="feat:` and the value parsed to `feat:` -- everything after the first
# space was silently dropped, including a trailer on a later line. Found by
# calling the parser directly rather than by reading it.
#
# A regex is the right tool because the value is delimited by quotes, not by
# whitespace. Both `-m x` and `--message=x` reach the same group.
MSG_RE = re.compile(
    r"""(?:^|\s)(?:-m|--message)(?:\s+|=)(?:"([^"]*)"|'([^']*)'|(\S+))""")

# `-F/--file` names a file whose whole contents become the message.
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
            # A message file we cannot read is not evidence of anything.
            pass
    return out


# `target_dir` was a third implementation of "which repo does this command touch",
# with its own regex. All three disagreed on `git --no-pager -C ../other commit`.
# `_hooklib.git_target_dir` is the one tokeniser now; the session cwd is "." here
# because this hook only reads git config, which is relative-safe.
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


def main() -> None:
    payload = load_payload()
    cmd = command_of(payload)
    if not cmd or not is_git_commit(cmd):
        return

    for msg in messages(cmd):
        found = first_hit(msg)
        if found:
            deny(f"This commit message carries AI attribution ({found!r}). "
                 f"Git history is permanent and CLAUDE.md forbids it outright. "
                 f"Remove that line and commit again -- the message is yours to "
                 f"write, so this hook refuses rather than editing it.")
            return

    author = configured_author(target_dir(cmd))
    found = first_hit(author)
    if found:
        deny(f"`user.name`/`user.email` in the target repo resolves to {found!r}, "
             f"so every commit there would carry the wrong author. Fix it with "
             f"`git config user.name` and `git config user.email` before "
             f"committing. No per-message check would have caught this.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

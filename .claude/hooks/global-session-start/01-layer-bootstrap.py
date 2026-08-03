"""global-session-start -- carries this capability layer into whatever repo the
session opened in.

Wired in `~/.claude/settings.json`, NOT in this repo's `.claude/settings.json`.
That is the whole point: a project hook only ever fires inside its own project,
so `on-repo-create/01-layer-import.py` -- which does the same install -- is
invisible in every repo that does not already have the layer, which is exactly
the set of repos that need it. This one runs everywhere.

Global, so read the blast radius first
--------------------------------------
This fires at the start of every session, in every folder, including ones that
are not the user's. It writes ~50 files when it acts. Four refusals bound it,
and only the first is the interesting one:

  1. the session's directory is a git repository ROOT
  2. it has no layer yet -- `.claude/skills/` absent
  3. it has no FOREIGN `.claude/` -- a directory holding someone else's
     `agents/` or `hooks/` is never merged into
  4. it is neither the source repo nor anywhere inside it

A subdirectory of a repo is refused rather than silently redirected to the root:
installing outside the directory the session opened in is a surprise, and the
one-line refusal names the root and the exact command instead.

Speaking
--------
It speaks when it acts, when it fails, and on the two near misses a user can do
something about. Everything else is silent -- a hook that comments on every
session in every folder gets switched off within a day. A silent action is
indistinguishable from no action, which is why the acting case always prints.

Idempotent by construction: after a successful install `.claude/skills/` exists,
so refusal 2 holds on every later session in that repo.

Relocation
----------
`~/.claude/settings.json` names this file by absolute path, and the source repo
is derived from that path (`parents[3]`) rather than hardcoded -- so the layer
stays a single source of truth and edits take effect on the next session with no
redeploy. Moving or renaming the source repo breaks the wiring, and its symptom
is Python failing to open the file at session start.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

HOOK = Path(__file__).resolve()
SOURCE_REPO = HOOK.parents[3]
INSTALLER = HOOK.parents[2] / "install.py"

# Shared with `on-repo-create/01-layer-import.py` on purpose. Both shell out to
# the same installer, and if one is ever reached from inside the other's run the
# guard stops the recursion. `06-artifact-autocommit.py` needed exactly this and
# its absence presented as a hang rather than an error.
GUARD = "UAIOS_LAYER_IMPORT_RUNNING"

# What proves the layer is already here. `.claude/` alone does not -- a repo can
# carry nothing but a `settings.local.json`, and that repo still wants the layer.
LAYER_MARKER = ".claude/skills"

# What proves someone else's layer is here. Merging into these would register our
# hooks over theirs, silently.
FOREIGN_MARKERS = (".claude/agents", ".claude/hooks")


def git(*args, cwd=None):
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=30)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def verdict(d):
    """(action, message). action is "install", "speak" or "silent"."""
    if not d.is_dir():
        return "silent", ""
    if d == SOURCE_REPO or SOURCE_REPO in d.parents:
        return "silent", ""

    top = git("rev-parse", "--show-toplevel", cwd=str(d))
    if not top:
        return "silent", ""
    try:
        root = Path(top).resolve()
    except (OSError, ValueError):
        return "silent", ""

    if root != d:
        # Not silently redirected to the root -- see the module docstring.
        if (root / LAYER_MARKER).exists() or SOURCE_REPO == root:
            return "silent", ""
        return "speak", (
            f"- this session opened in `{d}`, a subdirectory of the repo at "
            f"`{root}`, which has no capability layer. Installing outside the "
            f"session's own directory is not something a hook should decide, so "
            f"nothing was written. To do it: "
            f"`python \"{INSTALLER}\" --into \"{root}\"`")

    if (d / LAYER_MARKER).exists():
        return "silent", ""

    foreign = [m for m in FOREIGN_MARKERS if (d / m).exists()]
    if foreign:
        return "speak", (
            f"- `{d}` already has its own {', '.join('`' + f + '`' for f in foreign)}"
            f" — not merging the capability layer over it. If it should be "
            f"replaced, that is a decision to make explicitly: "
            f"`python \"{INSTALLER}\" --into \"{d}\"`")

    return "install", ""


def install(d):
    env = dict(os.environ)
    env[GUARD] = "1"
    # Both halves of the CLAUDE.md encoding gotcha, and both were needed: the
    # installer prints `—` and `→`, so the child needs PYTHONIOENCODING or it
    # raises UnicodeEncodeError on the Windows cp1252 default, and the parent
    # needs encoding= or it decodes that UTF-8 back as cp1252. Without the second
    # the entry-point advice reached the session as `stage 5 â€” 4 uncommitted`.
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run([sys.executable, str(INSTALLER), "--into", str(d)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"installer could not run: {exc}", []
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "").strip().splitlines()
        return False, "installer failed: " + (tail[-1] if tail else "no output"), []

    lines = p.stdout.splitlines()
    copied = [ln for ln in lines if ln.strip().startswith("copy ")]
    # `install.py` ends with "Where the chain should enter, given what is already
    # here:" and its bullets. That is the part worth carrying into the session --
    # the layer landing on work already in flight is the normal case, and without
    # it every install reads as "start at stage 1".
    entry = []
    for i, ln in enumerate(lines):
        if ln.startswith("Where the chain should enter"):
            entry = [x.strip() for x in lines[i + 1:] if x.strip().startswith("- ")]
            break
    return True, f"{len(copied)} path(s) copied", entry


def main():
    if os.environ.get(GUARD):
        return
    if not INSTALLER.is_file():
        return

    payload = load_payload()
    raw = payload.get("cwd") or os.getcwd()
    try:
        target = Path(raw).resolve()
    except (OSError, ValueError):
        return

    action, message = verdict(target)
    if action == "silent":
        return

    if action == "speak":
        lines = [message]
    else:
        done, detail, entry = install(target)
        if done:
            lines = [
                f"- **installed the capability layer into `{target}`** — {detail}, "
                f"from `{SOURCE_REPO}`. Its `.claude/settings.json` now registers "
                f"every hook from the source; remove any that do not apply here. "
                f"**The auto-commit commits at the end of every turn** — it never "
                f"pushes. Run `python tools/test_referenced_paths.py`; a copied "
                f"`CLAUDE.md` asserting counts from elsewhere is the usual first "
                f"failure. Nothing was committed."]
            if entry:
                lines.append("- where the chain should enter here:")
                lines += [f"  {e}" for e in entry]
        else:
            lines = [f"- **could not install the layer into `{target}`** — {detail}"]

    # Annotated because `reloadSkills` below is a bool: inferred from the two
    # string literals alone this is dict[str, str] and mypy rejects the append.
    out: dict[str, object] = {
        "hookEventName": "SessionStart",
        "additionalContext": "global-session-start:\n" + "\n".join(lines),
    }
    if action == "install":
        # Without this the install half-works, and the half that fails is the
        # point of it. Skills are loaded when the session starts; this hook runs
        # at that moment and then writes thirteen more, so the session that
        # installed the encyclopedia could not use it until a restart.
        # `reloadSkills` is a documented SessionStart output field.
        out["reloadSkills"] = True
    print(json.dumps({"hookSpecificOutput": out}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

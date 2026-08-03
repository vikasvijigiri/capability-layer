"""on-repo-create -- installs this capability layer into a newly created repo.

PostToolUse, matcher Bash|Write. Fires after a tool call that could have created
a directory, works out whether that directory is a *fresh git repository root*,
and if so runs `.claude/install.py --into <dir>` and says what it did.

Why an ACTING hook rather than a reminder
-----------------------------------------
`hooks_registry.json` states the rule for keeping a hook: it survives only if it
DENIES something irreversible, ACTS, or is a one-line INFORM. This one ACTS, in
the same way `post-run/06-artifact-autocommit.py` does -- and like that hook, it
always speaks its decision, because a silent action is indistinguishable from no
action, and a hook whose symptom is silence is the failure mode this repo has hit
most often.

What it can and cannot see
--------------------------
Only directories created **through a tool call**. `mkdir` or `git init` run in the
user's own terminal, or a folder made in Explorer, are invisible to every hook --
Claude Code emits events for its own tool calls, not for the filesystem. This was
stated before the hook was written rather than discovered afterwards, because the
obvious reading of "when a folder is created, import the layer" is not
implementable and quietly shipping the half that is would misrepresent it.

Five refusals, each for its own reason
--------------------------------------
The naive version -- import into any new directory -- is actively harmful:
`mkdir src/utils` would drop `.claude/` and `tools/` into a subdirectory, and any
build script running `mkdir` would do it repeatedly. So the target must satisfy
all five:

  1. it is a directory that exists now
  2. it is a git repository, and
  3. it is that repository's ROOT, not a subdirectory of one
  4. it has no `.claude/` yet -- so re-running is a no-op, not a re-copy
  5. it is neither the source repo nor anywhere inside it

Every refusal is logged to stdout at one line, so "it did nothing" always comes
with the reason. Never blocks; PostToolUse cannot undo the call anyway.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

HOOK = Path(__file__).resolve()
SOURCE_REPO = HOOK.parents[3]
INSTALLER = HOOK.parents[2] / "install.py"

# Re-entry guard. `install.py` writes files, and if anything downstream ever
# routes those writes back through the Write tool this hook would fire on its own
# output. `06-artifact-autocommit.py` needed exactly this guard and its absence
# presented as a hang rather than an error.
GUARD = "UAIOS_LAYER_IMPORT_RUNNING"


def git(*args, cwd=None):
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, timeout=30)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def candidates(payload):
    """Directories this tool call might have created. Over-collects on purpose --
    the five refusals below are what make the answer safe, not this function."""
    tool = payload.get("tool_name") or ""
    ti = payload.get("tool_input") or {}
    found: list[str] = []

    # Whether the directory was ASKED for matters, not just whether it is new.
    # A `mkdir`/`git init` is an intent to create; a `Write`'s parent directory is
    # incidental to writing a file. Only the first kind earns a spoken refusal --
    # otherwise every Write into any subdirectory of any other repo emits a line,
    # which it did, one per file, while this was being used.
    explicit = tool in ("Bash", "PowerShell")

    if explicit:
        cmd = ti.get("command") or ""
        # `mkdir [-p] a b c`, stopping at a shell separator or redirection.
        for m in re.finditer(r"\bmkdir\b((?:\s+-{1,2}\S+)*)((?:\s+[^\s;&|<>]+)+)", cmd):
            found += m.group(2).split()
        # `git init [dir]` and `git -C <dir> init`. Bare `git init` means cwd.
        for m in re.finditer(r"\bgit\b(?:\s+-C\s+(\S+))?[^;&|]*?\binit\b"
                             r"(?:\s+(?!-)([^\s;&|<>]+))?", cmd):
            found.append(m.group(1) or m.group(2) or ".")
    elif tool in ("Write", "Edit", "NotebookEdit"):
        fp = ti.get("file_path")
        if fp:
            found.append(str(Path(fp).parent))

    cwd = payload.get("cwd") or os.getcwd()
    out: list[tuple[Path, bool]] = []
    seen = set()
    for raw in found:
        raw = raw.strip().strip("'\"")
        if not raw:
            continue
        try:
            p = (Path(raw) if Path(raw).is_absolute() else Path(cwd) / raw).resolve()
        except (OSError, ValueError):
            continue
        if p not in seen:
            seen.add(p)
            out.append((p, explicit))
    return out


def verdict(d):
    """(should_import, reason).

    The source-repo checks come FIRST, and the order is load-bearing rather than
    stylistic. With the `.claude/` check ahead of them, every `Write` to a file in
    this repo resolved to the repo root, matched "already has a .claude/", and
    emitted a line -- a hook that comments on every single write. Refusals about
    this repo are not interesting and are now silent; only refusals about a
    plausible *other* target get spoken.
    """
    if not d.is_dir():
        return False, "does not exist as a directory"
    if d == SOURCE_REPO:
        return False, "is the source repo itself"
    if SOURCE_REPO in d.parents:
        return False, "is inside the source repo"
    if (d / ".claude").exists():
        return False, "already has a .claude/ -- nothing to import"
    top = git("rev-parse", "--show-toplevel", cwd=str(d))
    if not top:
        return False, "is not a git repository"
    try:
        root = Path(top).resolve()
        if root != d:
            # The full root path, not its basename. `src/physrun` inside the
            # `physrun` repo rendered as "physrun is not a repo root (its root is
            # physrun)", which reads as a contradiction.
            return False, f"is a subdirectory of the repo at {root}"
    except (OSError, ValueError):
        return False, "has an unresolvable git root"
    return True, "fresh git repo root with no .claude/"


def install(d):
    env = dict(os.environ)
    env[GUARD] = "1"
    # See global-session-start/01-layer-bootstrap.py: the installer prints `—`
    # and `→`, and on Windows the child raises UnicodeEncodeError without the
    # first line while the parent mojibakes without the second.
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run([sys.executable, str(INSTALLER), "--into", str(d)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"installer could not run: {exc}"
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "").strip().splitlines()
        return False, "installer failed: " + (tail[-1] if tail else "no output")
    copied = [ln.strip() for ln in p.stdout.splitlines() if ln.strip().startswith("copy ")]
    return True, f"{len(copied)} path(s) copied"


def main():
    if os.environ.get(GUARD):
        return
    payload = load_payload()
    if (payload.get("tool_name") or "") not in (
            "Bash", "PowerShell", "Write", "Edit", "NotebookEdit"):
        return
    if not INSTALLER.is_file():
        return

    lines = []
    for d, explicit in candidates(payload):
        ok, why = verdict(d)
        if not ok:
            # Spoken only when the directory was explicitly asked for AND the
            # refusal is a near miss. An incidental Write parent is never spoken,
            # and neither is anything about this repo.
            near_miss = "already has" in why or "subdirectory of the repo" in why
            if explicit and near_miss:
                lines.append(f"- skipped `{d}` — {why}")
            continue
        done, detail = install(d)
        if done:
            lines.append(
                f"- **imported the capability layer into `{d}`** — {detail}. "
                f"Its `.claude/settings.json` now registers every hook from this "
                f"repo; remove any that do not apply there. Run "
                f"`python tools/test_referenced_paths.py` in it — a copied "
                f"`CLAUDE.md` asserting counts from elsewhere is the usual first "
                f"failure. Nothing was committed.")
        else:
            lines.append(f"- **could not import into `{d}`** — {detail}")

    if not lines:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "on-repo-create:\n" + "\n".join(lines),
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

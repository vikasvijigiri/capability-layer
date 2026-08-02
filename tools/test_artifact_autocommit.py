"""Tests for post-run/06-artifact-autocommit.py.

The hook commits. So every case here runs against a throwaway git repo built in a
temp directory -- never this one -- and asserts on real `git log` / `git status`
output rather than on the hook's own report.

Two properties matter more than the rest, because they are the ones that make an
unreviewed automatic commit acceptable at all:

  1. It commits ONLY prose artefacts, and never anything under `.claude/`.
  2. It cannot sweep. Files already staged by someone else must survive the commit
     still staged and uncommitted -- this is the `git add .` failure in
     imehr/book-writer-plugin that put 49 files in this repo's index.

Run: python tools/test_artifact_autocommit.py
"""

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load():
    spec = importlib.util.spec_from_file_location(
        "autocommit", ROOT / ".claude/hooks/post-run/06-artifact-autocommit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["autocommit"] = mod
    spec.loader.exec_module(mod)
    return mod


def emit(mod) -> dict:
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.main()
    out = buf.getvalue().strip()
    return json.loads(out) if out else {}


def run(tmp: Path, *args) -> str:
    proc = subprocess.run(["git", *args], cwd=str(tmp),
                          capture_output=True, text=True, timeout=20)
    return proc.stdout.strip()


def new_repo(tmp: Path) -> None:
    run(tmp, "init", "-q")
    run(tmp, "config", "user.email", "t@example.com")
    run(tmp, "config", "user.name", "T")
    run(tmp, "commit", "-q", "--allow-empty", "-m", "base")


def write(tmp: Path, rel: str, body: str) -> None:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


mod = load()

# ------------------------------------------------------------------ is_artefact
# Pure classifier -- the whole safety boundary lives here, so it is tested alone.
for path, want, why in [
    ("LOG.md", True, "root knowledge doc"),
    ("HANDOFF.md", True, "root knowledge doc"),
    ("docs/specs/2026-01-01-x-design.md", True, "spec artefact"),
    ("docs/research/2026-01-01-x.md", True, "research artefact"),
    ("docs/plans/2026-01-01-x.md", True, "plan artefact"),
    ("decisions/2026-01-01-x.md", True, "decision record"),
    ("docs\\specs\\win-path.md", True, "backslash path normalises"),
    (".claude/skills/brainstormer/SKILL.md", False, ".claude is excluded outright"),
    (".claude/hooks/README.md", False, ".claude is excluded outright"),
    ("tools/test_hooks.py", False, "not .md"),
    ("docs/specs/data.json", False, "not .md"),
    ("CLAUDE.md", False, "root .md that is not a knowledge doc"),
    ("README.md", False, "root .md that is not a knowledge doc"),
    ("docs/archive/ARCHIVE.md", False, "archive is not an artefact root"),
    ("src/main.py", False, "code"),
]:
    check(f"is_artefact({path!r}) is {want} -- {why}", mod.is_artefact(path) is want)

# ------------------------------------------------------------- behaviour, on git
with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    new_repo(tmp)
    mod.REPO_ROOT = tmp

    marker = {"LOG.md": "old", "HANDOFF.md": "old"}
    mod.load_payload = lambda: {"stop_hook_active": False}
    mod.load_turn_marker = lambda: marker
    mod.doc_digests = lambda: {d: (tmp / d).read_text(encoding="utf-8")
                               if (tmp / d).exists() else ""
                               for d in ("LOG.md", "HANDOFF.md")}

    # --- does not fire when the boundary was not crossed
    write(tmp, "LOG.md", "old")
    write(tmp, "HANDOFF.md", "old")
    write(tmp, "docs/specs/s.md", "spec")
    check("silent when neither trigger doc changed this turn", emit(mod) == {})
    check("...and nothing was committed",
          run(tmp, "log", "--oneline") .count("\n") == 0)

    # --- fires once LOG.md moves, and commits the artefacts
    write(tmp, "LOG.md", "NEW")
    result = emit(mod)
    check("fires when LOG.md changed this turn", "hookSpecificOutput" in result)
    committed = run(tmp, "show", "--name-only", "--format=", "HEAD").split()
    # HANDOFF.md belongs here too: it is an uncommitted knowledge doc, and the unit
    # of work is the commit's subject, not the single file that tripped the trigger.
    check("commits every prose artefact, not just the one that fired the trigger",
          sorted(committed) == ["HANDOFF.md", "LOG.md", "docs/specs/s.md"],
          f"got {committed}")
    check("commit message names the boundary, not a tool",
          "knowledge-manager boundary" in run(tmp, "log", "-1", "--format=%B"))

    # --- the sweep test: someone else's staged file must survive untouched
    write(tmp, "HANDOFF.md", "NEW2")
    write(tmp, "src/unrelated.py", "print(1)")
    write(tmp, "other.txt", "x")
    run(tmp, "add", "src/unrelated.py", "other.txt")
    before_staged = sorted(run(tmp, "diff", "--cached", "--name-only").split())
    emit(mod)
    after_staged = sorted(run(tmp, "diff", "--cached", "--name-only").split())
    check("does not sweep files staged by someone else",
          before_staged == after_staged == ["other.txt", "src/unrelated.py"],
          f"before={before_staged} after={after_staged}")
    check("...and they are still uncommitted",
          "src/unrelated.py" not in run(tmp, "log", "--name-only", "--format="))

    # --- never touches code even when code changed in the same turn
    write(tmp, "LOG.md", "NEW3")
    write(tmp, "tools/x.py", "y = 1")
    emit(mod)
    check("never commits code alongside the artefacts",
          "tools/x.py" not in run(tmp, "show", "--name-only", "--format=", "HEAD"))

    # --- never touches .claude/, which holds executable hooks
    write(tmp, "LOG.md", "NEW4")
    write(tmp, ".claude/hooks/post-run/evil.md", "prose in an executable dir")
    emit(mod)
    check("never commits anything under .claude/",
          ".claude" not in run(tmp, "show", "--name-only", "--format=", "HEAD"))

    # --- loop guard
    mod.load_payload = lambda: {"stop_hook_active": True}
    write(tmp, "LOG.md", "NEW5")
    check("honours stop_hook_active", emit(mod) == {})
    mod.load_payload = lambda: {"stop_hook_active": False}

    # --- no marker means no boundary can be detected
    mod.load_turn_marker = lambda: None
    check("silent with no turn marker", emit(mod) == {})
    mod.load_turn_marker = lambda: marker

    # --- a doc-only turn with no artefacts still commits the doc
    write(tmp, "LOG.md", "NEW6")
    emit(mod)
    check("commits the knowledge doc on a turn with no other artefact",
          "LOG.md" in run(tmp, "show", "--name-only", "--format=", "HEAD"))

    # --- both failure paths are surfaced, never silent. Stubbing every git call
    # only ever exercises the first one, so `add` and `commit` are failed separately.
    real_git = mod.git

    mod.load_turn_marker = lambda: {"LOG.md": "x", "HANDOFF.md": "x"}
    write(tmp, "LOG.md", "NEW7")
    mod.git = lambda *a: (1, "", "simulated add failure")
    ctx = emit(mod).get("hookSpecificOutput", {}).get("additionalContext", "")
    check("reports a failed stage instead of failing silently",
          "could not stage" in ctx and "simulated add failure" in ctx,
          f"got {ctx[:120]}")

    mod.load_turn_marker = lambda: {"LOG.md": "y", "HANDOFF.md": "y"}
    write(tmp, "LOG.md", "NEW8")

    def fail_commit_only(*a):
        if a and a[0] == "commit":
            return 1, "", "simulated commit failure"
        return real_git(*a)

    mod.git = fail_commit_only
    ctx = emit(mod).get("hookSpecificOutput", {}).get("additionalContext", "")
    check("reports a failed commit instead of failing silently",
          "FAILED" in ctx and "simulated commit failure" in ctx, f"got {ctx[:120]}")

    # A failed commit must leave the index as it found it. Otherwise the artefacts
    # stay staged, session-start/03-index-baseline.py records them as "inherited"
    # next session, and pre-commit/06-index-scope-guard.py asks the user about files
    # this hook staged itself -- two new hooks false-positiving each other.
    check("...and says the index was restored, so the state is recoverable",
          "index was left as it was found" in ctx, f"got {ctx[:200]}")
    # The restore must be surgical, not a blanket reset: its own artefacts come back
    # out of the index, and the files staged by someone else earlier in this test stay
    # exactly where they were.
    staged_after = sorted(run(tmp, "diff", "--cached", "--name-only").split())
    check("...and its own artefact really is out of the index, not just claimed to be",
          "LOG.md" not in staged_after, f"still staged: {staged_after}")
    check("...while the files staged by someone else are untouched by the restore",
          staged_after == ["other.txt", "src/unrelated.py"], f"got {staged_after}")
    mod.git = real_git

# ------------------------------------------------------------------------ result
if failures:
    print(f"\n{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("\nAll artifact-autocommit tests passed")

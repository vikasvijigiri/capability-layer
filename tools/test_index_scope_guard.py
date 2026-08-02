"""Tests for pre-commit/06-index-scope-guard.py and session-start/03-index-baseline.py.

The pair closes the staging hole: `git add` was unguarded, and a commit spends
whatever the index holds, so 50 files staged in earlier sessions sat waiting to be
swept into an unrelated commit.

Two properties carry the design and are tested hardest:

  1. A commit that names its own paths (`git commit -- a.md b.md`) must NEVER be
     asked about -- it cannot sweep, and `post-run/06-artifact-autocommit.py` would
     deadlock against its own guard otherwise.
  2. `None` and `[]` baselines mean different things. `[]` is "the index was clean,
     everything staged is yours"; `None` is "we never found out". Collapsing them
     either disables the guard or makes it fire forever.

Run: python tools/test_index_scope_guard.py
"""

import importlib.util
import io
import json
import os
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


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def emit(mod) -> dict:
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.main()
    out = buf.getvalue().strip()
    return json.loads(out) if out else {}


guard = load(".claude/hooks/pre-commit/06-index-scope-guard.py", "index_guard")


def run(command: str, baseline, staged) -> dict:
    guard.load_payload = lambda: {"tool_name": "Bash", "tool_input": {"command": command}}
    guard.load_index_baseline = lambda: baseline
    guard.staged_paths = lambda *a: staged
    return emit(guard)


def asked(result: dict) -> bool:
    return (result.get("hookSpecificOutput", {}).get("permissionDecision") == "ask")


OLD = ["docs/archive/00-vision.md", ".claude/workflow.md"]
MINE = ["tools/new.py"]

# ------------------------------------------------------- trigger 1: blanket add
for cmd, want in [
    ("git add .", True),
    ("git add -A", True),
    ("git add --all", True),
    ("git add :/", True),
    ("git add *", True),
    ("git -C /repo add .", True),
    ("git add -- tools/new.py", False),
    ("git add tools/new.py docs/x.md", False),
    ("git add -u", False),                      # -u only restages tracked changes
    ("git status", False),
    ("git diff --cached", False),
    ("git log --all", False),                   # --all is not the add subcommand
    ("git commit --amend -m x", False),         # --amend must not read as `add`
    ('git commit -m "add the thing"', False),   # no blanket pathspec, so no ask
    ("cd sub && git add .", True),              # verb is not at position zero
    ("echo 'git add .'", True),                 # matches inside quotes, per the ADR
]:
    verb = "asks" if want else "is silent"
    check(f"blanket-add: {verb} for `{cmd}`",
          asked(run(cmd, [], [])) is want)

check("blanket-add ask names the safer alternative",
      "git add -- path/one" in run("git add .", [], []).get(
          "hookSpecificOutput", {}).get("permissionDecisionReason", ""))

check("blanket-add ask reports how many files are already staged",
      "index already holds 2" in run("git add .", [], OLD).get(
          "hookSpecificOutput", {}).get("permissionDecisionReason", ""))

# ------------------------------------------------- trigger 2: sweeping a commit
check("commit asks when inherited files are still staged",
      asked(run("git commit -m x", OLD, OLD + MINE)))

reason = run("git commit -m x", OLD, OLD + MINE).get(
    "hookSpecificOutput", {}).get("permissionDecisionReason", "")
check("...and counts inherited vs this session's separately",
      "2 file(s) that" in reason and "alongside 1 from this session" in reason,
      f"got {reason[:140]}")
check("...and offers both the pathspec commit and the unstage",
      "git commit -F" in reason and "git restore --staged" in reason)

check("commit silent when the inherited files were already dealt with",
      run("git commit -m x", OLD, MINE) == {})
check("commit silent when the index was clean at session start (baseline [])",
      run("git commit -m x", [], OLD + MINE) == {})
check("commit silent when the baseline is unknown (None, never collapse with [])",
      run("git commit -m x", None, OLD + MINE) == {})
check("commit silent when nothing is staged at all",
      run("git commit -m x", OLD, []) == {})
check("commit silent when git cannot answer what is staged",
      run("git commit -m x", OLD, None) == {})

# The property that would otherwise deadlock the artefact auto-commit against this guard.
check("a pathspec commit is never asked about -- it cannot sweep",
      run("git commit -F .msg -- LOG.md HANDOFF.md", OLD, OLD + MINE) == {})
check("a --dry-run commit is never asked about",
      run("git commit --dry-run -m x", OLD, OLD + MINE) == {})
check("a non-git command is never asked about",
      run("pytest -q", OLD, OLD + MINE) == {})

# ------------------------------------------------------------- escape hatch
os.environ["ALLOW_WIDE_STAGE"] = "1"
check("ALLOW_WIDE_STAGE=1 skips the blanket-add ask", run("git add .", [], []) == {})
check("ALLOW_WIDE_STAGE=1 skips the sweep ask",
      run("git commit -m x", OLD, OLD + MINE) == {})
del os.environ["ALLOW_WIDE_STAGE"]

# ------------------------------------- the baseline itself, against real git
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import _hooklib  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    for args in (["init", "-q"], ["config", "user.email", "t@e.com"],
                 ["config", "user.name", "T"],
                 ["commit", "-q", "--allow-empty", "-m", "base"]):
        subprocess.run(["git", *args], cwd=str(tmp), capture_output=True, text=True)

    check("staged_paths is [] on a clean index", _hooklib.staged_paths(tmp) == [])

    (tmp / "a.md").write_text("a", encoding="utf-8")
    (tmp / "b.py").write_text("b", encoding="utf-8")
    subprocess.run(["git", "add", "a.md", "b.py"], cwd=str(tmp), capture_output=True)
    check("staged_paths reports what is staged, sorted",
          _hooklib.staged_paths(tmp) == ["a.md", "b.py"])

    # Round-trip through the real state file, so the two halves are proven to agree.
    original = _hooklib.INDEX_BASELINE
    _hooklib.INDEX_BASELINE = tmp / "baseline.json"
    _hooklib.save_index_baseline(tmp)
    check("baseline round-trips through the state file",
          _hooklib.load_index_baseline() == ["a.md", "b.py"])

    _hooklib.INDEX_BASELINE = tmp / "missing.json"
    check("a missing baseline loads as None, not []",
          _hooklib.load_index_baseline() is None)

    (tmp / "corrupt.json").write_text("{not json", encoding="utf-8")
    _hooklib.INDEX_BASELINE = tmp / "corrupt.json"
    check("a corrupt baseline loads as None, not []",
          _hooklib.load_index_baseline() is None)

    # The hook itself, not just the helpers it calls. The first version of this file
    # named 03-index-baseline.py in its docstring and never executed it -- the exact
    # "prose claims coverage the wiring lacks" failure this repo has hit nine times.
    baseline_hook = load(".claude/hooks/session-start/03-index-baseline.py",
                         "index_baseline")
    baseline_hook.REPO_ROOT = tmp
    _hooklib.INDEX_BASELINE = tmp / "from-hook.json"
    baseline_hook.main()
    check("session-start/03-index-baseline.py writes the baseline when run",
          _hooklib.load_index_baseline() == ["a.md", "b.py"])

    # It must never raise, whatever it is pointed at -- a SessionStart hook that
    # throws would greet the user with a traceback on every new session.
    baseline_hook.REPO_ROOT = Path(tempfile.gettempdir()) / "definitely-not-a-repo"
    _hooklib.INDEX_BASELINE = tmp / "outside-repo.json"
    baseline_hook.main()
    check("...and records None, not [], when pointed outside a repo",
          _hooklib.load_index_baseline() is None)

    _hooklib.INDEX_BASELINE = original

    check("staged_paths returns None outside a repo",
          _hooklib.staged_paths(Path(tempfile.gettempdir()) / "definitely-not-a-repo")
          is None)

# ------------------------------------------------------------------------ result
if failures:
    print(f"\n{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("\nAll index-scope-guard tests passed")

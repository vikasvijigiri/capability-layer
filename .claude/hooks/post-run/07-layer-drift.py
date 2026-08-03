#!/usr/bin/env python3
"""Suggest `no-slop` once the `.claude/` layer has drifted far enough to reread.

Fires on Stop, after `06-artifact-autocommit.py` has checkpointed the turn.

The problem this solves
-----------------------
Layer decay accumulates across sessions rather than inside any one change, so
no diff review ever sees it: every individual edit looks fine and the overlap
between two skills only exists once both have been edited. Workflow stage 6
runs the full sweep before shipping, but shipping can be weeks away, and by then
the drift is large enough that the review is a project rather than a pass.

So this watches the layer between sweeps and names the skill when enough has
moved. It does NOT run the checks -- `tools/test_no_slop.py --scope layer` is
already in the per-turn suite. What it watches is *volume of change*, which no
check can see, because every one of those turns was individually green.

Two triggers, and the second is the important one
-------------------------------------------------
  volume     FILE_THRESHOLD distinct `.claude/` files touched since the last
             sweep. Content drift: descriptions widen, rules get restated.
  structure  a skill, agent or hook was ADDED or DELETED. Fires immediately at
             any count, because that is when trigger overlap appears -- a new
             skill's keywords are the one thing guaranteed to collide with an
             existing skill's, and no amount of editing one skill can cause it.

It suggests and never blocks. A hook cannot invoke a skill (confirmed in the
official docs, see `docs/research/2026-08-02-automating-the-git-chain.md`), and
`post-run/05-docs-gate.py` blocked a turn until a skill ran, deadlocked, and was
deleted on 2026-08-02.

Resetting is the skill's job, not this hook's
---------------------------------------------
A hook cannot tell that `no-slop` ran -- it sees tool calls, not skills. So the
skill records the sweep itself as its last step:

    python .claude/hooks/post-run/07-layer-drift.py --swept

Same shape as `systematic-debugging` owning its own `ISSUES.md` write. If the
skill runs and forgets, it gets suggested again -- a repeated nudge, never a
missed one.

**The marker is a commit SHA, not an empty file.** Deleting the state was the
first implementation and it did not work: the next turn re-read `git show HEAD`,
found the same commit's additions, and rebuilt the counter, so the nudge
repeated every turn until some later commit happened not to touch `.claude/`.
Drift is measured from the recorded SHA to HEAD, plus the worktree.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

# Same idiom as 06-artifact-autocommit.py: hooks/<event>/<file>.py -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[3]

STATE_NAME = "layer-drift.json"
FILE_THRESHOLD = 8

# A change to any of these is structural rather than editorial: it changes what
# exists, and therefore what can collide.
STRUCTURAL_DIRS = (".claude/skills/", ".claude/agents/", ".claude/hooks/")


def _state_path() -> Path:
    return REPO_ROOT / ".claude" / "hooks" / "state" / STATE_NAME


def git(*args) -> tuple[int, str]:
    try:
        proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
        return proc.returncode, proc.stdout.strip()
    except Exception:  # noqa: BLE001 -- a hook that raises can wedge a session
        return 1, ""


def speak(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "additionalContext": text,
    }}))


def load_state() -> dict:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"touched": [], "structural": []}


def save_state(state: dict) -> None:
    try:
        _state_path().parent.mkdir(parents=True, exist_ok=True)
        _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def swept() -> int:
    """Record that a sweep happened, at the commit it happened on.

    Deleting the state file is NOT enough, and shipping that was a real bug: the
    next turn re-read `git show HEAD`, which still reported the same commit's
    additions, so the counter rebuilt itself and the nudge repeated every turn
    until some later commit happened not to touch `.claude/`. A suggestion that
    fires every turn is one nobody reads.

    So the marker is a commit SHA, and drift is measured FROM it.
    """
    rc, head = git("rev-parse", "HEAD")
    save_state({"since": head if rc == 0 else "", "touched": [], "structural": {}})
    print(f"layer-drift counter cleared at {head[:8] if rc == 0 else 'unknown'}")
    return 0


def changed_layer_files(since: str = "") -> list[tuple[str, str]]:
    """(status, path) for `.claude/` files changed since the last sweep.

    The worktree is always read, because the auto-commit runs immediately before
    this hook: by the time we look, the turn's edits are usually committed rather
    than pending, and reading only one of the two would miss exactly the turns
    that matter.

    History is read from `since..HEAD` when a sweep has recorded a SHA, and from
    the last commit alone when none has. `since` that no longer resolves -- a
    rebase, a fresh clone -- falls back rather than failing: this hook must never
    be the reason a turn breaks.
    """
    history: tuple[str, ...]
    if since and git("cat-file", "-e", f"{since}^{{commit}}")[0] == 0:
        history = ("diff", "--name-status", f"{since}..HEAD")
    else:
        history = ("show", "--name-status", "--format=", "HEAD")

    out: list[tuple[str, str]] = []
    for args in (history, ("status", "--porcelain")):
        rc, text = git(*args)
        if rc != 0:
            continue
        for line in text.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            status, path = parts[0], parts[-1]
            if path.startswith(".claude/") and "/state/" not in path:
                out.append((status, path))
    return out


def main() -> int:
    if "--swept" in sys.argv:
        return swept()

    load_payload()  # consume stdin so the caller never blocks on a full pipe

    state = load_state()
    touched = set(state.get("touched", []))
    # Keyed by PATH, not by status+path. `git show` reports a new file as `A`
    # and `git status` reports the same file as `?`, so a set of "<status> <path>"
    # strings held one file twice -- this hook's own first real firing listed
    # 07-layer-drift.py on two lines and inflated the count it reported.
    # isinstance guards the old list format: a stale state file degrades to
    # empty rather than raising inside a hook, where the symptom is silence.
    raw = state.get("structural", {})
    structural: dict[str, str] = dict(raw) if isinstance(raw, dict) else {}
    since = state.get("since", "")

    for status, path in changed_layer_files(since):
        touched.add(path)
        # A/D in `git show`, ??/!! in `git status`. Renames count as both.
        if status[:1] in ("A", "D", "R", "?") and path.startswith(STRUCTURAL_DIRS):
            structural.setdefault(path, status[:1])

    # Anchor on first run, so an empty `since` is never sticky. Without this the
    # hook re-reads the SAME last commit every turn: state loss (a fresh clone, a
    # deleted state file) seeded `since: ""`, that seeding read HEAD's additions
    # as fresh drift, and the empty value was then written straight back -- so the
    # nudge repeated forever. Reporting HEAD once after losing the record is
    # right; reporting it every turn is the failure this hook exists to avoid.
    if not since:
        rc, head = git("rev-parse", "HEAD")
        since = head if rc == 0 else ""

    save_state({"since": since, "touched": sorted(touched), "structural": structural})

    if structural:
        speak(
            "`.claude/` gained or lost a skill, agent or hook since the last "
            "no-slop sweep:\n"
            + "".join(f"  {v} {k}\n" for k, v in sorted(structural.items()))
            + f"\n{len(touched)} layer file(s) touched in total.\n\n"
            "**Run the `no-slop` skill.** A new or removed capability is when "
            "trigger overlap appears, and no single edit can reveal it -- the "
            "collision exists between two files that were each fine alone.\n"
            "It clears this counter itself when the sweep completes."
        )
    elif len(touched) >= FILE_THRESHOLD:
        speak(
            f"{len(touched)} `.claude/` files have changed since the last "
            f"no-slop sweep (threshold {FILE_THRESHOLD}):\n"
            + "".join(f"  {p}\n" for p in sorted(touched)[:15])
            + "\n**Run the `no-slop` skill.** Every one of those turns was "
            "green -- decay is what accumulates between green turns.\n"
            "It clears this counter itself when the sweep completes."
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 -- a hook that raises can wedge a session
        sys.exit(0)

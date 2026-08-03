#!/usr/bin/env python3
"""Install this capability layer into another repository.

    python <source>/.claude/install.py --into /path/to/target
    python <source>/.claude/install.py --into /path/to/target --dry-run

Why this exists
---------------
Porting the layer by hand on 2026-08-03 needed four adaptations, and every one
was found by something breaking rather than by reading:

  1. `settings.json` must be MERGED, never copied. It is the only file that
     fires a hook, and a hook on disk it does not name never runs -- silently.
  2. `.gitignore` needs `.claude/hooks/state/`, or the auto-commit commits its
     own scratch report and then deletes it.
  3. `ruff.toml`, if present, needs `.claude/hooks/**` ignores. Every hook ends
     in a deliberate `except Exception: pass`, and isort would hoist the
     `_hooklib` import above the `sys.path.insert` that makes it resolvable --
     breaking every hook at once, silently.
  4. `CLAUDE.md` must be written fresh. The source's asserts things like "there
     is no application code here" and a hook count, both false elsewhere.

Four manual steps is a procedure someone gets wrong. This is the script.

What it deliberately does NOT do
--------------------------------
- Overwrite an existing `CLAUDE.md`, `settings.json` or `project-checks.json`.
  Those carry decisions; a fresh copy would silently discard them.
- Copy `hooks/state/` or `hooks/*.log`. Per-session scratch and session
  transcripts; the logs are the source's own prompt text, not layer content.
- Commit anything. The target repo's own gates decide that.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
SOURCE_REPO = SOURCE.parent

# Copied wholesale. Every one is repo-agnostic by construction -- verified by
# running test_process_router.py and test_referenced_paths.py in the target.
# `hooks_registry.json` is NOT listed: it lives inside `hooks/` and travels with
# it. Naming it here made the installer warn that the source was missing a file
# it had already copied.
#
# `install.py` IS listed, and was not until 2026-08-03. `commands/` carries
# `install-layer.md`, whose entire body is `python .claude/install.py --into
# <target>`. Copying the command without the script gave every target a slash
# command that could not run -- and a layer that cannot propagate itself is not
# portable, it is just copied once.
LAYER = ["skills", "agents", "routing", "commands", "hooks", "workflow.md",
         "install.py"]

# The layer's own tooling. Lives in tools/ rather than .claude/ because
# `_projectchecks.detect_checks` looks for `tools/test_*.py`, and moving it
# would mean the layer could not check itself.
TOOLS = ["run_checks.py", "run_hook.py", "test_referenced_paths.py",
         "test_process_router.py", "test_no_slop.py", "check_config_json.py"]

# Never copied out of `hooks/`, and each for a different reason. Passed to
# `shutil.ignore_patterns`, so these are glob patterns, not names.
#
# This set was declared and then never referenced until 2026-08-03 -- it read as
# a guard and enforced nothing. `settings.json` and `project-checks.json` were
# excluded only by their absence from LAYER, which is a coincidence of that
# list rather than a stated rule.
#
# `*.log` is the one that mattered. `_hooklib.write_log` records tool payloads
# and prompt text verbatim, which is why `.gitignore` says they must never be
# committed -- and the installer was copying 3.5 MB of the SOURCE session's
# transcripts into every target. The target's `.gitignore` then hid them, so
# nothing ever reported it.
NEVER_IN_HOOKS = ("state", "__pycache__", "*.log")

# Never copied at the top level of `.claude/`. Both carry decisions that a fresh
# copy would silently discard; `ensure_stubs`/`merge_settings` handle them.
NEVER_AT_ROOT = {"settings.json", "project-checks.json"}

GITIGNORE_BLOCK = """
# Hook state: per-turn bookkeeping and the diagnose-loop scratch report,
# rewritten constantly and meaningless outside the session that wrote it.
.claude/hooks/state/

# Hook logs. `_hooklib.write_log` appends here and the entries capture tool
# payloads verbatim, so they contain whatever the session contained.
#
# This line is why the block exists. The source repo has ignored these since
# day one, so nothing here ever noticed -- but the installer only wrote the
# state/ line, and a fresh target committed `artifact-create.log` on its first
# `git add -A`. The layer's own suite then went red on the layer's own log,
# reporting a credential pattern and two `TBD` markers inside the payloads.
# Found by installing into a virgin repo and using it, not by reading.
.claude/hooks/*.log
"""

RUFF_BLOCK = '''
# Hooks end in a deliberate `except Exception: pass` -- a hook that raises can
# wedge a session, and every one documents this in its own docstring.
#
# I001 is off here and the reason is load-bearing, not stylistic. Every hook
# does `sys.path.insert(...)` and THEN `from _hooklib import ...`; isort wants
# to hoist that import above the line that makes it resolvable, which breaks
# every hook at once, silently.
".claude/hooks/**" = ["S110", "S112", "I001"]
'''

CLAUDE_STUB = """# {name} — CLAUDE.md

<!-- Written by .claude/install.py. Replace this with what is actually true
here; it is a bootloader, not documentation. Keep it under ~150 lines. -->

## The commit loop

`post-run/06-artifact-autocommit.py` commits what changed at the end of every
turn, as a `wip:` checkpoint, but only if the branch is not protected, no
changed file matches a credential pattern, no schema migration is present, the
change is under `max_files`, and the fast-tier checks pass.

**It commits without asking.** That is deliberate and it is the main thing to
know about this layer. It never pushes.

On red it writes `.claude/hooks/state/check-failure-report.md` and asks for
`systematic-debugging`; three strikes on the same failure and it escalates.

## Checks

    python tools/run_checks.py --tier fast --require-test

Resolves this project's own lint, typecheck and test commands from marker files
and runs them. `--require-test` fails when no test ran at all -- passing and
having nothing to run are different facts.

**A repo with no tests cannot auto-commit code** until `"test": false` is set in
`.claude/project-checks.json`, stating deliberately that there are none.

## Gotchas

- All hooks are `python …`. Without Python on PATH they fail silently.
- A hook's failure symptom is silence. After editing one, fire it against a
  realistic payload; a clean diff proves nothing.
"""

PROJECT_CHECKS_STUB = {
    "_note": ("What `the checks pass` means here. Read by "
              ".claude/hooks/_projectchecks.py, which the auto-commit gates on "
              "and which /verify calls, so the two cannot disagree. Each key "
              "takes a command, a list of commands, or false to disable that "
              "check as a stated decision. An absent key means detect it."),
    "timeout": 300,
    "max_files": 25,
}


class Report:
    def __init__(self, dry: bool) -> None:
        self.dry = dry
        self.lines: list[str] = []
        self.warnings: list[str] = []

    def did(self, what: str) -> None:
        self.lines.append(("would " if self.dry else "") + what)

    def warn(self, what: str) -> None:
        self.warnings.append(what)


def copy_layer(target: Path, r: Report) -> None:
    dest_root = target / ".claude"
    for name in LAYER:
        if name in NEVER_AT_ROOT:
            # LAYER is edited by hand; this makes the rule hold rather than
            # depending on someone remembering it.
            r.warn(f"{name} is in LAYER but must never be copied -- skipped")
            continue
        src = SOURCE / name
        if not src.exists():
            r.warn(f"source is missing {name} -- skipped")
            continue
        dst = dest_root / name
        if r.dry:
            r.did(f"copy .claude/{name}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(*NEVER_IN_HOOKS))
        else:
            shutil.copy2(src, dst)
        r.did(f"copy .claude/{name}")

    tools_dst = target / "tools"
    for name in TOOLS:
        src = SOURCE_REPO / "tools" / name
        if not src.exists():
            r.warn(f"source is missing tools/{name} -- skipped")
            continue
        if not r.dry:
            tools_dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tools_dst / name)
        r.did(f"copy tools/{name}")


def merge_settings(target: Path, r: Report) -> None:
    """Union the hook entries. Never clobber -- the target may run its own."""
    src = json.loads((SOURCE / "settings.json").read_text(encoding="utf-8"))
    dst_path = target / ".claude" / "settings.json"

    if not dst_path.exists():
        if not r.dry:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            dst_path.write_text(json.dumps(src, indent=2) + "\n", encoding="utf-8")
        r.did("create .claude/settings.json from the source's hook registrations")
        r.warn("settings.json registers every source hook. Remove any that have "
               "nothing to do here -- a registered hook whose file is missing "
               "exits 2, and PreToolUse reads that as deny.")
        return

    existing = json.loads(dst_path.read_text(encoding="utf-8"))
    merged = dict(existing)
    merged.setdefault("hooks", {})
    added = 0
    for event, blocks in src.get("hooks", {}).items():
        have = json.dumps(merged["hooks"].get(event, []), sort_keys=True)
        for block in blocks:
            if json.dumps(block, sort_keys=True) not in have:
                merged["hooks"].setdefault(event, []).append(block)
                added += 1
    if not r.dry and added:
        dst_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    r.did(f"merge {added} hook block(s) into the existing settings.json")


def ensure_gitignore(target: Path, r: Report) -> None:
    """Add whichever ignore lines are missing, not the block as a unit.

    Checking for one line and skipping the whole block was a real bug: a repo
    installed before `.claude/hooks/*.log` was added already had the state/
    line, so it never received the new one and kept committing its hook logs.
    An installer that is only correct on a virgin target is not an installer.
    """
    path = target / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    have = {ln.strip() for ln in text.splitlines()}
    wanted = [ln for ln in GITIGNORE_BLOCK.splitlines()
              if ln.strip() and not ln.lstrip().startswith("#")]
    missing = [ln for ln in wanted if ln.strip() not in have]

    if not missing:
        r.did("skip .gitignore -- every hook path is already ignored")
        return
    if not r.dry:
        # Re-append the whole commented block on a first install, but only the
        # bare missing lines on a top-up, so the reasons are not duplicated.
        addition = (GITIGNORE_BLOCK if len(missing) == len(wanted)
                    else "\n" + "\n".join(missing) + "\n")
        path.write_text(text + addition, encoding="utf-8")
    r.did(f"add {len(missing)} ignore line(s) to .gitignore: {', '.join(missing)}")


def ensure_ruff(target: Path, r: Report) -> None:
    path = target / "ruff.toml"
    if not path.exists():
        r.did("skip ruff.toml -- not present, so nothing lints the hooks")
        return
    text = path.read_text(encoding="utf-8")
    if ".claude/hooks/**" in text:
        r.did("skip ruff.toml -- hook ignores already present")
        return
    if "[lint.per-file-ignores]" in text:
        head, sep, tail = text.partition("[lint.per-file-ignores]")
        new = head + sep + "\n" + RUFF_BLOCK.strip() + "\n" + tail
    else:
        new = text + "\n[lint.per-file-ignores]\n" + RUFF_BLOCK.strip() + "\n"
    if not r.dry:
        path.write_text(new, encoding="utf-8")
    r.did("add .claude/hooks/** ignores to ruff.toml")


def ensure_stubs(target: Path, r: Report) -> None:
    claude_md = target / "CLAUDE.md"
    if claude_md.exists():
        r.did("keep the existing CLAUDE.md")
        r.warn("CLAUDE.md was not touched. If it came from another repo it may "
               "assert things that are false here -- counts, 'no application "
               "code', hook names.")
    else:
        if not r.dry:
            claude_md.write_text(CLAUDE_STUB.format(name=target.name),
                                 encoding="utf-8")
        r.did("write a CLAUDE.md stub")

    checks = target / ".claude" / "project-checks.json"
    if checks.exists():
        r.did("keep the existing project-checks.json")
    else:
        if not r.dry:
            checks.parent.mkdir(parents=True, exist_ok=True)
            checks.write_text(json.dumps(PROJECT_CHECKS_STUB, indent=2) + "\n",
                              encoding="utf-8")
        r.did("write a project-checks.json stub")


def assess(target: Path) -> list[str]:
    """Where should the chain ENTER, given the state this repo is already in?

    The layer is almost never installed into an empty repo. It lands on work
    already in flight -- a half-finished branch, a plan with three tasks ticked,
    a tree with uncommitted changes -- and `workflow.md` says plainly that the
    numbers are a dependency order, not an arrival order. Nothing read that
    table, so every install started at stage 1 regardless of what was there.

    This reads the tree and names the stage. Signals only; it never acts.
    """
    def git(*a) -> str:
        try:
            p = subprocess.run(["git", *a], cwd=str(target), capture_output=True,
                               text=True, timeout=30)
            return p.stdout.strip() if p.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    notes: list[str] = []
    dirty = [ln for ln in git("status", "--porcelain").splitlines() if ln.strip()]
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    protected = branch in ("main", "master", "develop", "release")

    plans = sorted((target / "docs" / "plans").glob("*.md")) if (
        target / "docs" / "plans").is_dir() else []
    specs = sorted((target / "docs" / "specs").glob("*.md")) if (
        target / "docs" / "specs").is_dir() else []
    has_task = (target / "TASK.md").is_file()

    # An unfinished plan is the strongest signal there is: it names the work,
    # the order, and how far it got.
    for plan in plans:
        try:
            body = plan.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        todo, done = body.count("- [ ]"), body.count("- [x]")
        if todo:
            notes.append(
                f"stage 4 `executing-plans` — {plan.name} has {done} step(s) "
                f"ticked and {todo} left")
            break
    else:
        if specs and not plans:
            notes.append(f"stage 3 `writing-plans` — {len(specs)} spec(s) in "
                         f"docs/specs/ with no plan beside them")
        elif has_task:
            notes.append("stage 1 `task-brief` — TASK.md exists; read it before "
                         "assuming the work is new")

    if dirty:
        notes.append(f"stage 5 `verifying-work` — {len(dirty)} uncommitted "
                     f"path(s); prove what is there before adding to it")
    if branch and not protected:
        ahead = git("rev-list", "--count", f"origin/{branch}..HEAD") or git(
            "rev-list", "--count", "HEAD")
        notes.append(f"stage 7 `code-review` — on `{branch}`"
                     + (f", {ahead} commit(s) unreviewed" if ahead else ""))
    if protected:
        notes.append(f"`{branch}` is protected — the auto-commit will refuse "
                     f"until you branch. That is the first thing to do.")

    tests = list(target.rglob("test_*.py")) + list(target.rglob("*_test.go")) \
        + list(target.rglob("*.test.ts")) + list(target.rglob("*.spec.ts"))
    if not tests:
        notes.append('no tests found — set `"test": false` in '
                     ".claude/project-checks.json or no code can auto-commit")

    if not notes:
        notes.append("clean tree, nothing in flight — stage 1 `task-brief`")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--into", required=True, help="target repository root")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--assess", action="store_true",
                    help="only report where the chain should enter; install nothing")
    args = ap.parse_args()

    target = Path(args.into).resolve()
    # Before the source-repo guard on purpose: "where should the chain enter"
    # is a fair question about any repository, including this one.
    if args.assess and target.is_dir():
        print(f"Where the chain should enter, for {target.name}:\n")
        for note in assess(target):
            print(f"  - {note}")
        return 0
    if not target.is_dir():
        print(f"FAIL: {target} is not a directory", file=sys.stderr)
        return 1
    if target == SOURCE_REPO:
        print("FAIL: target is the source repo", file=sys.stderr)
        return 1

    r = Report(args.dry_run)
    copy_layer(target, r)
    merge_settings(target, r)
    ensure_gitignore(target, r)
    ensure_ruff(target, r)
    ensure_stubs(target, r)

    print(f"{'DRY RUN — ' if args.dry_run else ''}installed into {target}\n")
    for line in r.lines:
        print(f"  {line}")
    if r.warnings:
        print("\nRead these:")
        for w in r.warnings:
            print(f"  ! {w}")

    print("\nNext, in the target:")
    print("  python tools/test_referenced_paths.py   # prose that names things")
    print("  python tools/test_process_router.py     # skills, agents, routing")
    print("  python tools/test_no_slop.py            # layer decay, mechanical half")
    print("  python tools/test_no_slop.py --scope repo   # the pre-ship sweep")
    print("  python tools/run_checks.py --tier fast  # the project's own checks")
    print("\nThe auto-commit COMMITS at the end of every turn. It never pushes.")

    # Landing on work already in flight is the normal case, not the edge case.
    # `workflow.md` says plainly that the stage numbers are a dependency order
    # rather than an arrival order, but nothing read that table, so every
    # install effectively began at stage 1 no matter what was already here.
    print("\nWhere the chain should enter, given what is already here:")
    for note in assess(target):
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

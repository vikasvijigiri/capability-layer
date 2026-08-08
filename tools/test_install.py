#!/usr/bin/env python3
"""Tests for .claude/install.py -- putting the layer into somebody else's repo.

This is the one script here whose bugs land in a repository that is not this one,
so the properties under test are about what it must never destroy:

  - `CLAUDE.md` and `.claude/project-checks.json` are never overwritten. One says
    what the target repository is; the other says what "the checks pass" means
    there. A fresh copy asserting this repo's facts is worse than no file.
  - `settings.json` is merged, never replaced. A target keeping its own hooks
    keeps every one of them.
  - `--dry-run` writes nothing at all. Not "writes less" -- nothing.
  - It refuses to install into itself.

The file did not exist until 2026-08-07, while `~/.claude/commands/install-layer.md`
and the global `CLAUDE.md` had both documented it for days. Both references live
outside this repository, so `test_referenced_paths.py` -- which is repo-scoped --
could never have caught it. This suite is the scoped-in half of that.

Run: python tools/test_install.py
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
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
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


check("the installer exists at the path every doc names",
      (ROOT / ".claude" / "install.py").is_file(),
      "~/.claude/commands/install-layer.md and the global CLAUDE.md both run "
      ".claude/install.py by absolute path")

inst = load(".claude/install.py", "install_mod")


def fresh_repo() -> Path:
    d = Path(tempfile.mkdtemp()) / "target"
    d.mkdir()
    for args in (["init", "--quiet"],
                 ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=str(d), capture_output=True, text=True)
    return d


# --- a clean install ---------------------------------------------------------

target = fresh_repo()
(target / "src").mkdir()
(target / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")

actions, warnings = inst.plan(target)
check("the plan names no missing source file", not warnings, str(warnings))
check("the plan covers the skills", any(
    a[0].as_posix().startswith(".claude/skills/") for a in actions))
check("the plan covers the hooks", any(
    a[0].as_posix().startswith(".claude/hooks/") for a in actions))
check("the plan covers the tools", any(
    a[0].as_posix().startswith("tools/") for a in actions))
check("the plan covers the harness contract",
      {Path("AGENTS.md"), Path("harnesses.json")} <= {a[0] for a in actions})

# Runtime residue must not travel. Importing this repo's attempt counters and
# green refs into another repository would make its very first derived state a
# statement about work that happened somewhere else.
planned = {a[0].as_posix() for a in actions}
check("hook runtime state is not copied",
      not any(p.startswith(".claude/hooks/state/") for p in planned),
      str([p for p in planned if "hooks/state" in p]))
check("__pycache__ is not copied",
      not any("__pycache__" in p for p in planned))
check("workflow-state is not copied",
      not any(p.startswith(".claude/workflow-state") for p in planned))

inst.apply(target, actions)

check("skills landed as <name>/SKILL.md, the only shape that is visible",
      (target / ".claude" / "skills" / "repo-recon" / "SKILL.md").is_file())
check("agents landed", (target / ".claude" / "agents" / "task-implementer.md").is_file())
check("the workflow policy landed", (target / ".claude" / "workflow.md").is_file())
check("the tools landed", (target / "tools" / "resume.py").is_file()
      and (target / "tools" / "recon.py").is_file())
check("settings.json was created", (target / ".claude" / "settings.json").is_file())
check("a project-checks stub was written",
      (target / ".claude" / "project-checks.json").is_file())

stub = json.loads((target / ".claude" / "project-checks.json").read_text(encoding="utf-8"))
check("the stub does NOT decide `test` for the target",
      "test" not in stub,
      "a repo with no tests must state that deliberately -- an absent check and "
      "a passing one are different facts, and the auto-commit distinguishes them")
check("...but it says so in the file itself", "_first_decision" in stub)

check("CLAUDE.md is not created for a target that has none",
      not (target / "CLAUDE.md").exists(),
      "a copied CLAUDE.md asserts this repo's facts about another repo")

registered = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
source_settings = json.loads(
    (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
check("every source hook event is registered in the target",
      set(source_settings["hooks"]) <= set(registered["hooks"]),
      f"missing {sorted(set(source_settings['hooks']) - set(registered['hooks']))}")


def commands_in(settings: dict) -> set[str]:
    return {
        h.get("command")
        for blocks in (settings.get("hooks") or {}).values()
        for block in blocks
        for h in (block.get("hooks") or [])
    }


check("...and every hook command with it",
      commands_in(source_settings) <= commands_in(registered),
      f"missing {sorted(commands_in(source_settings) - commands_in(registered))}")


# --- idempotence -------------------------------------------------------------

again, _ = inst.plan(target)
check("a second plan over an installed target rewrites nothing",
      not [a for a in again if a[1] in ("create", "overwrite")],
      str([a for a in again if a[1] in ("create", "overwrite")][:4]))
inst.apply(target, again)
twice = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
check("...and re-merging settings.json does not duplicate a hook",
      len(commands_in(twice)) == len(commands_in(registered)),
      f"{len(commands_in(twice))} vs {len(commands_in(registered))}")


# --- the preserve rules, which are the whole point ---------------------------

keeper = fresh_repo()
(keeper / "CLAUDE.md").write_text("# Their project\n\nTheir rules.\n", encoding="utf-8")
(keeper / ".claude").mkdir()
(keeper / ".claude" / "project-checks.json").write_text(
    json.dumps({"test": False, "_why": "no tests here yet"}), encoding="utf-8")
(keeper / ".claude" / "settings.json").write_text(json.dumps({
    "hooks": {"SessionStart": [{"hooks": [
        {"type": "command", "command": "python their_own_hook.py"}]}]},
    "theme": "light",
}), encoding="utf-8")

keeper_actions, _ = inst.plan(keeper)
inst.apply(keeper, keeper_actions)

check("an existing CLAUDE.md survives untouched",
      (keeper / "CLAUDE.md").read_text(encoding="utf-8")
      == "# Their project\n\nTheir rules.\n")
check("an existing project-checks.json survives untouched",
      json.loads((keeper / ".claude" / "project-checks.json")
                 .read_text(encoding="utf-8"))["test"] is False,
      "overwriting it would silently re-enable a check the owner disabled")

merged = json.loads((keeper / ".claude" / "settings.json").read_text(encoding="utf-8"))
check("the target's own hook survives the merge",
      "python their_own_hook.py" in commands_in(merged), str(commands_in(merged)))
check("...and the source hooks are added alongside it",
      commands_in(source_settings) <= commands_in(merged),
      f"missing {sorted(commands_in(source_settings) - commands_in(merged))}")
check("...and unrelated settings keys are preserved",
      merged.get("theme") == "light",
      "the merge must touch `hooks` and nothing else")

check("PRESERVE and MERGE do not overlap",
      not (set(inst.PRESERVE) & set(inst.MERGE)),
      "a file that is both preserved and merged has two contradictory rules")


# --- --dry-run writes nothing ------------------------------------------------


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git/" not in p.relative_to(root).as_posix()
    }


def quiet(argv: list[str]) -> int:
    """Run the installer with its output captured.

    The refusals print to stderr by design, and `run_checks.py` surfaces a
    suite's last stderr line as the failure detail -- so an uncaptured refusal
    message makes a passing suite read as a failing one.
    """
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        return inst.main(argv)


dry = fresh_repo()
(dry / "existing.txt").write_text("do not touch\n", encoding="utf-8")
before = snapshot(dry)
rc = quiet(["--into", str(dry), "--dry-run"])
after = snapshot(dry)
check("--dry-run exits 0", rc == 0, str(rc))
check("--dry-run wrote nothing at all", before == after,
      f"added {sorted(set(after) - set(before))[:5]}")


# --- refusals ----------------------------------------------------------------

check("installing into the source layer is refused",
      quiet(["--into", str(ROOT), "--dry-run"]) == 2)
check("installing into a subdirectory of the source is refused",
      quiet(["--into", str(ROOT / "tools"), "--dry-run"]) == 2,
      "a nested install would copy the layer over itself")
check("a nonexistent target is refused rather than created",
      quiet(["--into", str(Path(tempfile.mkdtemp()) / "nope")]) == 2)


# --- settings merge, directly ------------------------------------------------

src = json.dumps({"hooks": {"Stop": [{"hooks": [
    {"type": "command", "command": "a.py"},
    {"type": "command", "command": "b.py"}]}]}})
dst = json.dumps({"hooks": {"Stop": [{"hooks": [
    {"type": "command", "command": "a.py"}]}]}})
out, notes = inst.merge_settings(src, dst)
parsed = json.loads(out)
check("merging adds only the hook that was missing",
      sorted(commands_in(parsed)) == ["a.py", "b.py"], str(commands_in(parsed)))
check("...and reports exactly what it added", len(notes) == 1, str(notes))

out2, notes2 = inst.merge_settings(src, "")
check("an absent target settings.json is treated as empty, not as an error",
      sorted(commands_in(json.loads(out2))) == ["a.py", "b.py"], str(notes2))

try:
    inst.merge_settings(src, "{ this is not json")
    check("a corrupt target settings.json fails loudly", False,
          "a stray comma in settings.json silently turns the whole hook layer "
          "off -- the one failure here with no symptom")
except SystemExit as exc:
    check("a corrupt target settings.json fails loudly rather than being replaced",
          "not valid JSON" in str(exc), str(exc)[:120])


# --- the entry-point report is honest ---------------------------------------

check("a non-git target is told so first",
      "not a git repository" in inst.entry_point(Path(tempfile.mkdtemp())),
      "without git there is no auto-commit, no branch guard and no derived state")

big = fresh_repo()
(big / "src").mkdir()
for n in range(30):
    (big / "src" / f"mod{n}.py").write_text("x = 1\n", encoding="utf-8")
check("an existing codebase with no plan is routed to reconnaissance",
      "repo-recon" in inst.entry_point(big), inst.entry_point(big))

planned_repo = fresh_repo()
(planned_repo / "docs" / "plans").mkdir(parents=True)
(planned_repo / "docs" / "plans" / "2026-01-01-x.md").write_text("# p\n", encoding="utf-8")
check("a target that already has a plan is routed to the state engine",
      "resume.py" in inst.entry_point(planned_repo), inst.entry_point(planned_repo))

check("an empty target starts at the framing stage",
      "task-brief" in inst.entry_point(fresh_repo()),
      inst.entry_point(fresh_repo()))


# --- the installed layer validates itself in the target ---------------------
#
# The real test of portability. A copied CLAUDE.md asserting counts from
# somewhere else is the usual first failure, which is exactly why CLAUDE.md is
# not copied.

proc = subprocess.run(
    [sys.executable, "tools/test_process_router.py"],
    cwd=str(target), capture_output=True, text=True, timeout=180,
    stdin=subprocess.DEVNULL,   # a hook inheriting this pipe blocks in load_payload()
    env={**dict(__import__("os").environ), "PYTHONIOENCODING": "utf-8"},
)
check("the installed layer passes its own router check in the target",
      proc.returncode == 0,
      (proc.stdout + proc.stderr).strip().splitlines()[-1][:200]
      if (proc.stdout + proc.stderr).strip() else "no output")

for d in (target, keeper, dry, big, planned_repo):
    shutil.rmtree(d.parent, ignore_errors=True)


# --- upgrade: the three outcomes, and which one is safe to be wrong about -----
#
# `install` overwrites any file whose bytes differ. Right the first time, wrong
# the second: once a team customises a skill, re-running destroys it silently.
# `upgrade` compares the target's CURRENT bytes to the hash recorded at install
# and splits the difference three ways -- unchanged-here (take the upstream
# change), edited-here (never overwrite without --force), and no-baseline (treat
# as edited, because "I do not know" and "unchanged" must not be one answer).

up = fresh_repo()
inst.apply(up, inst.plan(up)[0])

manifest = json.loads((up / ".claude" / "layer-manifest.json").read_text(encoding="utf-8"))
check("the manifest records a version", manifest.get("version") == inst.MANIFEST_VERSION,
      str(manifest.get("version")))
check("...and a hash per owned file", isinstance(manifest.get("files"), dict)
      and len(manifest["files"]) > 100, str(len(manifest.get("files") or {})))
check("...hashed from the SOURCE, so a failed copy cannot claim success",
      manifest["files"].get(".claude/workflow.md")
      == inst.file_hash(inst.SOURCE / ".claude/workflow.md"))
check("the manifest does not hash itself", 
      inst.MANIFEST.as_posix() not in manifest["files"])

edited = up / ".claude" / "skills" / "no-slop" / "SKILL.md"
MARK = "<!-- ours -->"
edited.write_text(edited.read_text(encoding="utf-8") + "\n" + MARK + "\n",
                  encoding="utf-8")
untouched = up / ".claude" / "workflow.md"
before_untouched = untouched.read_text(encoding="utf-8")

recorded = inst._layer_hashes(up)
check("a recorded hash is readable back", bool(recorded), str(len(recorded)))
check("an edited file no longer matches its recorded hash",
      recorded[".claude/skills/no-slop/SKILL.md"] != inst.file_hash(edited))
check("...while an untouched one still does",
      recorded[".claude/workflow.md"] == inst.file_hash(untouched))

rc = quiet(["--into", str(up), "--upgrade"])
check("upgrade exits 0", rc == 0, str(rc))
check("the local edit SURVIVES an upgrade",
      MARK in edited.read_text(encoding="utf-8"),
      "this is the whole point of the mode")
check("...and the untouched file is still correct",
      untouched.read_text(encoding="utf-8") == before_untouched)

rc = quiet(["--into", str(up), "--upgrade", "--force"])
check("--force overwrites the edit, because that is what it means",
      MARK not in edited.read_text(encoding="utf-8"), str(rc))

# A v1 manifest has no hashes. Every difference must then read as a local edit --
# refusing an upstream change is recoverable; discarding a team's work is not.
v1 = fresh_repo()
inst.apply(v1, inst.plan(v1)[0])
(v1 / ".claude" / "layer-manifest.json").write_text(
    json.dumps({"version": 1, "paths": []}), encoding="utf-8")
v1_edited = v1 / ".claude" / "skills" / "no-slop" / "SKILL.md"
v1_edited.write_text("replaced entirely", encoding="utf-8")
quiet(["--into", str(v1), "--upgrade"])
check("a v1 manifest degrades to refusing every difference",
      v1_edited.read_text(encoding="utf-8") == "replaced entirely",
      "with no baseline, overwriting is a guess with someone else's work")

for d in (up, v1):
    shutil.rmtree(d.parent, ignore_errors=True)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All install tests passed")

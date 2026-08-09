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

import contextlib
import importlib.util
import io
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

# Framing and planning merged into one owner on 2026-08-09, so the empty-repo
# entry point and the has-TASK.md one now name the same skill at different
# stages of it. Both are asserted: a merge that collapsed them into one string
# would lose the distinction the message exists to draw.
check("an empty target starts at the framing stage",
      "writing-plans" in inst.entry_point(fresh_repo()),
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


# --- a target's lint configuration is its decision, not the layer's ----------
#
# `ruff.toml` and `mypy.ini` sat in FILES until 2026-08-08. FILES copies
# unconditionally and overwrites anything that differs, so installing the layer
# into a product repo silently replaced its tuned lint rules with this
# repository's. They are SEED now: created when absent, untouched when present.

cfg = fresh_repo()
(cfg / "ruff.toml").write_text("line-length = 79\n", encoding="utf-8")
(cfg / "mypy.ini").write_text("[mypy]\nstrict = True\n", encoding="utf-8")
inst.apply(cfg, inst.plan(cfg)[0])

check("an existing ruff.toml is NOT overwritten",
      "79" in (cfg / "ruff.toml").read_text(encoding="utf-8"),
      "a product's lint rules are a decision the layer must not discard")
check("an existing mypy.ini is NOT overwritten",
      "strict = True" in (cfg / "mypy.ini").read_text(encoding="utf-8"))

seeded = fresh_repo()
inst.apply(seeded, inst.plan(seeded)[0])
check("...but a repo with none is given a working starting point",
      (seeded / "ruff.toml").is_file() and (seeded / "mypy.ini").is_file(),
      "otherwise the layer's own hooks and tools go unchecked in the target")

# The seeded mypy config must cover the TARGET, not this repository's layout.
# `files = .claude/hooks, tools` shipped for a day: a product installing the
# layer typechecked the LAYER and never its own source, while run_checks
# reported `typecheck` green -- a gate asserting something true about the wrong
# code, which is worse than an absent one because it reads as coverage.
seeded_mypy = (seeded / "mypy.ini").read_text(encoding="utf-8")
check("the seeded mypy config is repository-level",
      "files = ." in seeded_mypy,
      "review and verification are repo-level or they are theatre")
# The DIRECTIVE, not the commentary. This file explains the old value in a
# comment in order to explain the fix, and a check that cannot tell an
# explanation from a declaration fails on its own documentation -- the same trap
# `test_referenced_paths.py` records about its budget-word scan.
_mypy_directives = [ln.strip() for ln in seeded_mypy.splitlines()
                    if ln.strip() and not ln.strip().startswith("#")]
check("...and does not hardcode this repository's directories",
      not any(".claude/hooks" in ln for ln in _mypy_directives),
      str([ln for ln in _mypy_directives if ".claude" in ln]))
check("...while still excluding the staged payload, which duplicates tools/",
      "build" in seeded_mypy, "mypy refuses two modules with one name")

# Lint is repo-level already, and must stay that way: `ruff check .` takes the
# whole tree, so the only thing that could narrow it is an `include` key.
seeded_ruff = (seeded / "ruff.toml").read_text(encoding="utf-8")
check("the seeded ruff config does not narrow itself to the layer",
      "include" not in seeded_ruff.split("[lint]")[0],
      "an include list here would scope linting to whatever this repo happens "
      "to contain")

# --- uninstall: what may be removed, and what must never be -----------------
#
# `uninstall` mirrors `upgrade`: same manifest, same hash comparison, opposite
# consequence. The risk is not symmetric though -- a wrong `upgrade` keeps a file
# it could have refreshed, a wrong `uninstall` deletes somebody's work. So the
# protected set is asserted by name, and the edited case is asserted with a real
# edit rather than a fixture flag.

un = fresh_repo()
inst.apply(un, inst.plan(un)[0])

_removable = ".claude/workflow.md"
_edited = ".claude/skills/no-slop/SKILL.md"
(un / _edited).write_text("locally edited\n", encoding="utf-8")

remove, kept_edited, kept_protected, refused = inst.uninstall_plan(un)

check("uninstall_plan offers to remove an untouched installed file",
      _removable in remove, f"remove={len(remove)} paths")
check("uninstall_plan keeps a file edited since install",
      _edited in kept_edited and _edited not in remove,
      f"edited file must survive; kept_edited={_edited in kept_edited}")

# The trap this whole verb has to avoid. `write_manifest` counts `merge` actions
# as layer-owned, so settings.json IS in the manifest -- but it may carry hooks
# the host had before the layer arrived, and nothing recorded what those were.
check("uninstall_plan never offers to remove the merged settings.json",
      ".claude/settings.json" not in remove,
      "merged host configuration; deleting it destroys hooks nobody recorded")

# Resolved at Gate 1: a repo that adopted the layer's lint config now depends on
# it, so removing the layer must not break ruff and CI in the same step.
for _seed in ("ruff.toml", "mypy.ini"):
    if (un / _seed).is_file():
        check(f"uninstall_plan keeps the seeded {_seed}",
              _seed not in remove, "SEED files are kept and named")

check("uninstall_plan keeps the manifest out of the removable set",
      inst.MANIFEST.as_posix() not in remove,
      "the caller removes it last, so an interrupted run stays resumable")

check("uninstall_plan's three lists are disjoint",
      not (set(remove) & set(kept_edited))
      and not (set(remove) & set(kept_protected))
      and not (set(kept_edited) & set(kept_protected)),
      "a path in two lists means the caller's behaviour depends on iteration order")

check("uninstall_plan writes nothing",
      (un / _removable).is_file() and (un / ".claude" / "settings.json").is_file(),
      "it plans; applying is main()'s job")

# A target the layer never touched has no manifest, and the honest answer is
# three empty lists -- not "remove everything I can see".
_virgin = fresh_repo()
check("uninstall_plan refuses a target with no manifest",
      inst.uninstall_plan(_virgin) == ([], [], [], []),
      "no manifest means nothing here was installed by this layer")

# --- uninstall: applying it ---------------------------------------------------
#
# End to end on a real temp repo, because the whole verb is filesystem effects
# and `uninstall_plan` deliberately has none. Exit code proves nothing here; each
# check reads the tree back.

def _installed_repo():
    d = fresh_repo()
    (d / "src").mkdir()
    (d / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    inst.apply(d, inst.plan(d)[0])
    return d


# A dry run must leave the tree byte-identical. Measured by hashing every file
# before and after, not by trusting the flag.
dry = _installed_repo()
_before = {p.relative_to(dry).as_posix(): inst.file_hash(p)
           for p in dry.rglob("*") if p.is_file() and ".git" not in p.parts}
rc_dry = inst.main(["--uninstall", "--into", str(dry), "--dry-run"])
_after = {p.relative_to(dry).as_posix(): inst.file_hash(p)
          for p in dry.rglob("*") if p.is_file() and ".git" not in p.parts}
check("uninstall --dry-run exits 0", rc_dry == 0, f"rc={rc_dry}")
check("uninstall --dry-run leaves the tree byte-identical",
      _before == _after,
      f"changed: {sorted(set(_before) ^ set(_after))[:3]}")

# The real thing.
gone = _installed_repo()
(gone / ".claude" / "skills" / "no-slop" / "SKILL.md").write_text(
    "locally edited\n", encoding="utf-8")
rc = inst.main(["--uninstall", "--into", str(gone)])
check("uninstall exits 0", rc == 0, f"rc={rc}")
check("uninstall removed an untouched installed file",
      not (gone / ".claude" / "workflow.md").is_file())
check("uninstall kept the file that was edited after install",
      (gone / ".claude" / "skills" / "no-slop" / "SKILL.md").is_file(),
      "an edited file is the user's work, not the layer's")
check("uninstall never removed the merged settings.json",
      (gone / ".claude" / "settings.json").is_file(),
      "merged host configuration")
check("uninstall left the host's own code alone",
      (gone / "src" / "app.py").is_file(), "the host's code is not the layer's")
check("uninstall removed the manifest last",
      not (gone / inst.MANIFEST).is_file(),
      "with it gone the verb is idempotent by construction")
check("uninstall pruned the directories it emptied",
      not (gone / ".claude" / "agents").is_dir(),
      "an empty tree of directories is residue")

# Safe to run twice: the manifest is gone, so the second run has nothing to
# claim and must refuse rather than delete by pattern.
rc2 = inst.main(["--uninstall", "--into", str(gone)])
check("a second uninstall refuses instead of guessing", rc2 == 2, f"rc={rc2}")

# --upgrade and --uninstall are opposite operations; asking for both is a
# mistake that must fail loudly rather than doing half of each.
_both = _installed_repo()
try:
    inst.main(["--uninstall", "--upgrade", "--into", str(_both)])
    _rejected = False
except SystemExit as exc:
    _rejected = exc.code != 0
check("--uninstall and --upgrade together are refused", _rejected,
      "argparse must reject the combination, not silently pick one")

# --- the report must describe what actually happened -------------------------
#
# Both of these were found by `verifying-work`, not by this suite, and both are
# the same class: the verb behaved correctly and said something else.
#
# `TASK.md`'s Done Check is "an edited installed file survives AND is named in
# the report". Survival was asserted above; naming was not, so a regression that
# silenced the kept-list would have shipped green.

_rep = _installed_repo()
_rep_edited = ".claude/skills/no-slop/SKILL.md"
(_rep / _rep_edited).write_text("locally edited\n", encoding="utf-8")
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    inst.main(["--uninstall", "--into", str(_rep)])
_report = _buf.getvalue()

check("the report names the file it kept as edited",
      _rep_edited in _report,
      "silence about a kept file is the failure this verb exists to avoid")
check("the report names the protected settings.json",
      ".claude/settings.json" in _report)
check("the report names a kept SEED file",
      "ruff.toml" in _report)

# The manifest IS deleted, and deliberately -- it is what makes a second run
# refuse. Reporting it under "kept" told the reader the opposite.
#
# EVERY line mentioning it, not the first. The first version of this check read
# only the text before the first occurrence, and red-green proved it worthless:
# reintroducing the defect produced BOTH `removed last  .claude/layer-manifest.json`
# AND `kept (edited) .claude/layer-manifest.json`, the correct line came first,
# and the suite stayed green. A check that passes on the defect it names is worse
# than no check, because it is counted as coverage.
_manifest_lines = [ln for ln in _report.splitlines()
                   if inst.MANIFEST.as_posix() in ln]
check("the report mentions the manifest exactly once",
      len(_manifest_lines) == 1, f"lines: {_manifest_lines}")
check("the report does not claim the manifest was kept",
      not any("kept" in ln for ln in _manifest_lines),
      f"it is removed last; calling it kept contradicts the tree. {_manifest_lines}")
check("...and says it was removed last",
      any("removed last" in ln for ln in _manifest_lines),
      f"lines: {_manifest_lines}")
check("...and the manifest is genuinely gone",
      not (_rep / inst.MANIFEST).is_file())

shutil.rmtree(_rep.parent, ignore_errors=True)


# --- the manifest is untrusted input ----------------------------------------
#
# `.claude/layer-manifest.json` is tracked, committed, and travels with every
# clone, and `uninstall` is most useful on a repository somebody else wrote. A
# crafted manifest deleted a file in the target's PARENT directory until
# `code-review` demonstrated it -- after three `verifying-work` passes and an
# eight-mutation sweep had all reported clean, none of which asked whether the
# input could be hostile.
#
# The fixture supplies a MATCHING sha256 for the outside file, so the hash
# comparison would happily call it "installed and untouched". Containment has to
# be checked before classification, not after.

_evil_root = Path(tempfile.mkdtemp())
_precious = _evil_root / "PRECIOUS.txt"
_precious.write_text("outside the target\n", encoding="utf-8")
_evil = _evil_root / "repo"
_evil.mkdir()
(_evil / ".claude").mkdir()
(_evil / ".claude" / "layer-manifest.json").write_text(json.dumps({
    "version": 2,
    "paths": ["../PRECIOUS.txt", "/etc/passwd", ".claude/workflow.md"],
    "files": {"../PRECIOUS.txt": inst.file_hash(_precious)},
}), encoding="utf-8")

_er, _ek, _ep, _eref = inst.uninstall_plan(_evil)
check("a manifest entry escaping the target is refused, not removed",
      "../PRECIOUS.txt" not in _er and "../PRECIOUS.txt" in _eref,
      f"remove={_er} refused={_eref}")
check("an absolute manifest entry is refused too",
      "/etc/passwd" not in _er and "/etc/passwd" in _eref,
      "target / '/etc/passwd' is '/etc/passwd' under pathlib join semantics")
check("refused entries are reported, never silently dropped",
      len(_eref) == 2,
      "a silent skip makes a partial uninstall look complete")

_eerr = io.StringIO()
with contextlib.redirect_stderr(_eerr):
    inst.main(["--uninstall", "--into", str(_evil)])
_estderr = _eerr.getvalue()

check("the file outside the target still exists after a real uninstall",
      _precious.is_file(),
      "this is the defect code-review demonstrated; it must stay dead")

# Classifying an entry as refused and TELLING the user are two properties, and
# a mutation sweep proved the second had no assertion behind it: silencing the
# whole refused block left the suite green. Silence is how a partial uninstall
# looks complete.
check("refused entries are named on stderr, not just classified",
      "../PRECIOUS.txt" in _estderr and "REFUSED" in _estderr,
      f"stderr was: {_estderr[:120]!r}")

# `--force` on a destructive verb reads as "yes, really" and does nothing here.
# Also unasserted until the same sweep.
_ferr = io.StringIO()
_fdir = _installed_repo()
with contextlib.redirect_stderr(_ferr), contextlib.redirect_stdout(io.StringIO()):
    inst.main(["--uninstall", "--force", "--into", str(_fdir)])
check("--force with --uninstall says it has no effect",
      "--force has no effect" in _ferr.getvalue(),
      f"stderr was: {_ferr.getvalue()[:120]!r}")

# "The manifest is missing" and "the manifest names nothing actionable" are
# different facts. They shared one message, so a user was told to look for a
# file that was in front of them. Both messages are asserted, because a single
# assertion on the exit code cannot tell them apart -- both return 2.
_nomani = fresh_repo()
_e1 = io.StringIO()
with contextlib.redirect_stderr(_e1):
    inst.main(["--uninstall", "--into", str(_nomani)])
check("a target with no manifest is told the manifest is missing",
      f"no {inst.MANIFEST.as_posix()}" in _e1.getvalue(),
      f"stderr: {_e1.getvalue()[:100]!r}")

_empty = fresh_repo()
(_empty / ".claude").mkdir()
(_empty / ".claude" / "layer-manifest.json").write_text(json.dumps({
    "version": 2, "paths": [inst.MANIFEST.as_posix()], "files": {}}), encoding="utf-8")
_e2 = io.StringIO()
with contextlib.redirect_stderr(_e2):
    inst.main(["--uninstall", "--into", str(_empty)])
check("a manifest that names nothing actionable says so, not 'missing'",
      "names no removable path" in _e2.getvalue()
      and f"no {inst.MANIFEST.as_posix()}" not in _e2.getvalue(),
      f"stderr: {_e2.getvalue()[:110]!r}")

for _d in (_nomani, _empty):
    shutil.rmtree(_d.parent, ignore_errors=True)

shutil.rmtree(_evil_root, ignore_errors=True)
shutil.rmtree(_fdir.parent, ignore_errors=True)


# --- uninstall reaches the CLI ----------------------------------------------
#
# The verb must resolve AND be payload-only. Payload-only is the load-bearing
# half: a target being uninstalled still has `.claude/install.py` in it, and
# loading that copy would make `SOURCE` the target -- the module would be
# deleting the file it is running from.

# `capability_layer/` is the PACKAGE, and the payload is `.claude/` plus
# `tools/`. An installed target therefore has this suite but no CLI module to
# load, and `test_package.py` runs exactly that combination -- it installs the
# wheel into a fresh repo and runs the repo's own tier. Skipping with a reason is
# this repo's convention for a check whose subject is absent; failing would make
# every installed target red for a file it is not supposed to have.
if not (ROOT / "capability_layer" / "cli.py").is_file():
    print("SKIP: no capability_layer/cli.py -- the console entry point is part "
          "of the package, not of the installed payload, so the uninstall verb's "
          "CLI wiring is unmeasured here")
else:
    _cli = load("capability_layer/cli.py", "cl_cli_mod")
    check("the CLI knows the uninstall verb", "uninstall" in _cli._TARGETS,
          f"verbs: {sorted(_cli._TARGETS)}")
    check("uninstall dispatches to the installer module",
          _cli._TARGETS.get("uninstall") == ".claude/install.py")
    check("uninstall is payload-only, never the target's own copy",
          "uninstall" in _cli._PAYLOAD_ONLY,
          "loading the target's copy would alias SOURCE to the target")
    check("uninstall reaches install.py through --uninstall",
          _cli._MODE_FLAG.get("uninstall") == "--uninstall",
          f"mode flags: {_cli._MODE_FLAG}")
    check("...and upgrade still reaches it through --upgrade",
          _cli._MODE_FLAG.get("upgrade") == "--upgrade",
          "the map replaced an if-chain; the first entry must still work")
    check("the CLI usage text names the verb",
          "uninstall" in (_cli.__doc__ or ""),
          "a verb absent from the usage block is a verb nobody runs")

for _d in (dry, gone, _both):
    shutil.rmtree(_d.parent, ignore_errors=True)


for _d in (un, _virgin):
    shutil.rmtree(_d.parent, ignore_errors=True)


for _d in (cfg, seeded):
    shutil.rmtree(_d.parent, ignore_errors=True)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All install tests passed")

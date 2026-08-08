#!/usr/bin/env python3
"""Does the built package actually put a working layer into somebody else's repo.

Everything else here checks the source tree. This checks the *artifact*, which is
the only thing a product repo ever sees, and it is the one place a packaging bug
can hide: the first wheel built from this repository shipped
`.claude/settings.local.json` -- the file granting `Bash(git push:*)` -- plus
`project-checks.json` and this repo's runtime hook state, while `pyproject.toml`
listed every one of them as excluded. Hatchling's `force-include` ignores
`exclude`. The build succeeded, the wheel installed, and nothing was wrong until
someone read the zip.

So this reads the zip, and then goes further: installs it into a clean venv,
installs THAT into a fresh git repository, and requires the repository's own tier
to come back green. A wheel that builds is not a wheel that works.

    python tools/test_package.py

**Slow tier.** It builds a wheel and creates two virtual environments, which takes
tens of seconds and hundreds of megabytes -- far too expensive for the fast tier
that gates every auto-commit.

Prerequisites are SKIPPED AND NAMED, never passed over in silence: no `build`
module, no network for `pip`, or no disk space prints a NOTE saying exactly which
one and what was therefore not checked. `.claude/constitution.md` Article V is the
whole reason that distinction is written down rather than assumed.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []
skipped: list[str] = []

# Free space below which a wheel build and two venvs cannot be attempted. Not a
# guess: the venvs alone are ~60MB each and the staged payload plus wheel is a
# few more. Checked up front so the failure is "no disk" rather than a build
# backend crashing with an error that reads like a code defect -- which is
# exactly what happened on 2026-08-08, when mypy's cache write failed under a
# full disk and reported as a type error.
MIN_FREE_BYTES = 400 * 1024 * 1024


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def last_line(proc) -> str:
    """The line worth quoting from a subprocess, or a stated absence of one."""
    text = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return text.splitlines()[-1] if text else "no output"


def skip(what: str, why: str) -> None:
    print(f"NOTE: skipped {what} -- {why}")
    skipped.append(what)


def run(args: list[str], cwd: Path | None = None, timeout: int = 900):
    return subprocess.run(
        args, cwd=str(cwd) if cwd else None, capture_output=True,
        encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
        timeout=timeout,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def venv_bin(venv: Path, name: str) -> Path | None:
    for candidate in (venv / "Scripts" / f"{name}.exe", venv / "Scripts" / name,
                      venv / "bin" / name):
        if candidate.is_file():
            return candidate
    return None


# --- prerequisites, each named if missing -----------------------------------

free = shutil.disk_usage(ROOT).free
if free < MIN_FREE_BYTES:
    skip("the whole suite",
         f"{free // (1024*1024)}MB free, need {MIN_FREE_BYTES // (1024*1024)}MB. "
         f"A build under a full disk fails in ways that read as code defects.")
    print(f"\n{len(skipped)} step(s) skipped, 0 failed")
    sys.exit(0)

if run([sys.executable, "-c", "import build"]).returncode != 0:
    skip("the whole suite", "`build` is not installed -- pip install build")
    print(f"\n{len(skipped)} step(s) skipped, 0 failed")
    sys.exit(0)

# --- stage and build ---------------------------------------------------------

# Delete the staged payload FIRST, so the build hook has to produce it. This
# suite used to run `tools/stage_payload.py` and then build -- the order a human
# follows, and the opposite of what pip does. pip clones into a fresh directory
# that has never been staged, so every check here passed while
# `pip install git+https://...` died with
#
#     FileNotFoundError: Forced include not found: .../build/payload
#
# Building from an already-staged tree cannot detect that, by construction.
payload_dir = ROOT / "build" / "payload"
if payload_dir.exists():
    shutil.rmtree(payload_dir)
check("the staged payload is absent before the build starts",
      not payload_dir.exists(),
      "otherwise this proves nothing about a fresh clone")

for old in glob.glob(str(ROOT / "dist" / "*.whl")):
    Path(old).unlink()
built = run([sys.executable, "-m", "build", "--wheel"], cwd=ROOT)
wheels = sorted(glob.glob(str(ROOT / "dist" / "*.whl")))
check("a wheel builds from a tree with NO staged payload, as pip does",
      built.returncode == 0 and bool(wheels), last_line(built))
check("...because the build hook staged it, not a human",
      payload_dir.is_dir() and any(payload_dir.rglob("*")),
      "hatch_build.py:initialize() runs before force-include resolves")

if not wheels:
    print(f"\n{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)

wheel = Path(wheels[-1])
print(f"     {wheel.name}")

# --- read the artifact, not the config that produced it ----------------------

zf = zipfile.ZipFile(wheel)
names = zf.namelist()

check("the payload carries the skills",
      any("payload/.claude/skills/repo-recon/SKILL.md" in n for n in names))
check("...and the suites, which are what prove an install worked",
      len([n for n in names if "/payload/tools/test_" in n]) >= 20)
check("...and settings.json, which the merge needs as a SOURCE",
      any(n.endswith("payload/.claude/settings.json") for n in names),
      "without it every install registers zero hooks, silently")
check("...and install.py, so the target can install elsewhere",
      any(n.endswith("payload/.claude/install.py") for n in names))

FORBIDDEN = {
    "settings.local.json": "grants Bash(git push:*)",
    "project-checks.json": "states what green means in ONE repository",
    "llm-env.md": "this repository's unenforced opinion",
    "__pycache__": "build residue",
    ".claude/hooks/state/": "this repository's attempt counters and green refs",
    "workflow-state": "runtime residue",
}
for token, why in FORBIDDEN.items():
    hits = [n for n in names if token in n]
    check(f"the wheel does not ship {token}", not hits, f"{why}; found {hits[:2]}")

check("the wheel ships no root CLAUDE.md",
      not any(n.endswith("payload/CLAUDE.md") for n in names),
      "it asserts facts true only in the repository that wrote it")

ABSOLUTE = re.compile(r"C:[/\\]Users|/home/[a-z][a-z0-9_-]*/|/Users/[A-Za-z]")
leaks = []
for name in names:
    if not name.endswith((".py", ".md", ".json", ".toml", ".ini", ".yml", ".yaml")):
        continue
    if ABSOLUTE.search(zf.read(name).decode("utf-8", "replace")):
        leaks.append(name)
check("no shipped file contains an absolute path", not leaks,
      f"{leaks[:3]} -- a path from the build machine breaks on every other one")

# --- install it, and use it --------------------------------------------------

sandbox = Path(tempfile.mkdtemp(prefix="pkgtest-"))
try:
    venv = sandbox / "venv"
    made = run([sys.executable, "-m", "venv", str(venv)])
    if made.returncode != 0:
        skip("the install-and-use half", f"venv creation failed: {made.stderr[:120]}")
    else:
        installed = run([str(venv_bin(venv, "python")), "-m", "pip", "install",
                         "--quiet", str(wheel)])
        check("pip installs the wheel into a clean venv",
              installed.returncode == 0, installed.stderr.strip()[-160:])

        # The PATH-independent route, checked FIRST because it is the one that
        # survives the common Windows case: pip cannot write site-packages, does
        # a --user install, and the Scripts/ directory it uses is not on PATH.
        # The package is then installed, importable and uninvocable. That is what
        # happened to the first person who followed this project's README.
        module = run([str(venv_bin(venv, "python")), "-m", "capability_layer",
                      "--version"])
        check("`python -m capability_layer` works without any PATH entry",
              module.returncode == 0 and module.stdout.strip(),
              (module.stdout + module.stderr).strip()[-160:])

        cl = venv_bin(venv, "capability-layer")
        short = venv_bin(venv, "cl")
        check("the console script is installed", cl is not None and cl.is_file(),
              f"looked in {venv}/Scripts and {venv}/bin")
        check("...and the short alias with it", short is not None)

        if cl:
            version = run([str(cl), "--version"])
            check("`capability-layer --version` works",
                  version.returncode == 0 and version.stdout.strip(),
                  version.stdout.strip() or version.stderr.strip()[:120])

            product = sandbox / "product"
            product.mkdir()
            for args in (["init", "--quiet"],
                         ["config", "user.email", "t@example.com"],
                         ["config", "user.name", "t"]):
                run(["git", *args], cwd=product)
            (product / "app.py").write_text(
                "def charge():\n    raise NotImplementedError\n", encoding="utf-8")
            (product / "test_app.py").write_text(
                "def test_charge():\n    assert True\n", encoding="utf-8")
            run(["git", "add", "-A"], cwd=product)
            run(["git", "commit", "--quiet", "-m", "product"], cwd=product)

            done = run([str(cl), "install", "--into", str(product)])
            check("`capability-layer install` succeeds in a fresh repo",
                  done.returncode == 0, done.stderr.strip()[-160:])
            check("...and the skills land in a shape the harness can see",
                  (product / ".claude" / "skills" / "repo-recon" / "SKILL.md").is_file())
            check("...and settings.json registers the hooks",
                  (product / ".claude" / "settings.json").is_file()
                  and len(json.loads(
                      (product / ".claude" / "settings.json").read_text(encoding="utf-8")
                  ).get("hooks", {})) > 0)
            check("...and nothing forbidden came with it",
                  not (product / ".claude" / "settings.local.json").exists()
                  and not (product / ".claude" / "rules" / "llm-env.md").exists())

            # The acceptance criterion. Everything above can pass on a layer that
            # does not run.
            tier = run([str(venv_bin(venv, "python")), "tools/run_checks.py",
                        "--tier", "all", "--require-test"], cwd=product)
            last = last_line(tier)
            check("the installed layer passes the target's OWN tier",
                  tier.returncode == 0 and "PASS" in last, last[:200])
            print(f"     {last[:150]}")
finally:
    shutil.rmtree(sandbox, ignore_errors=True)

print()
if skipped:
    print(f"{len(skipped)} step(s) skipped and named: {', '.join(skipped)}")
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All package tests passed")

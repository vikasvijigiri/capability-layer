#!/usr/bin/env python3
"""Cluster A -- target-matrix conformance for objectives 15, 16, 25, 27.

    python tools/test_target_matrix.py

One small, synthetic fixture corpus, built fresh in a temp directory every
run and deleted at the end -- never checked in. `tools/test_install.py`
already builds its Python and Node install targets this way; this follows
the same precedent along a second axis (repository STAGE and STACK rather
than install mechanics), and keeping the corpus generated rather than
tracked preserves the objective-14 payload-size win recorded in `TASK.md`
("Make the layer portable": 1,586,874 -> 1,172,851 bytes).

Four objectives, one corpus -- this is `docs/specs/2026-08-21-qualitative-
objective-metrics.md`'s Cluster A, and the whole reason it clusters:

  15  Stage-agnostic          -- install/recon/run_checks against 5 named
                                  stages (greenfield, partial, legacy,
                                  broken, undocumented) without crashing.
  16  Repository-agnostic     -- recon reports each stage's REAL structure,
                                  never a constant; and resolving checks
                                  inside a fixture never leaks THIS repo's
                                  own gating commands into it.
  25  Technology-agnostic     -- a non-Python, non-Node stack (a bare Go
                                  layout) gets no Python lint config seeded
                                  and is recognised as `go`, not silently
                                  ignored.
  27  Progressively adoptable -- installing moves nothing: every
                                  pre-existing file stays at its own path,
                                  and the target's own pre-existing command
                                  still runs and prints the same thing.

Objective 13 (universal/generic) is already Green via
`.claude/adapters/*.json`'s `conformance` field and
`tools/test_portability_contract.py` -- nothing here re-measures it.

Every install/recon/check-resolution call below is made IN-PROCESS, not via
`subprocess` per fixture. `tools/run_checks.py --tier fast` spawns one
subprocess per resolved check; doing that once per fixture on top of a
fresh interpreter start per fixture would multiply the fast tier's
wall-clock cost for a repository-portability property that does not need a
real subprocess boundary to prove it -- `test_install.py`'s own
`_pc.resolve_checks(_nopy, ...)` direct call is the precedent.
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


inst = load(".claude/install.py", "install_mod_tm")
recon = load("tools/recon.py", "recon_mod_tm")
pc = load(".claude/hooks/_projectchecks.py", "pc_mod_tm")


def _git_init(d: Path) -> None:
    # stdin=DEVNULL on every spawn here, not just the sys.executable one below --
    # this file also loads `.claude/hooks/_projectchecks.py` in-process, and
    # `test_no_slop.py --scope layer`'s `check_hook_spawn_stdin()` flags ANY
    # subprocess call in a file that touches hooks and lacks it, on the
    # (correct, cheap-to-satisfy) theory that an inherited pipe under the tier
    # blocks a child that ever falls through to `load_payload()`'s stdin read.
    for args in (["init", "--quiet"],
                 ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=str(d), capture_output=True, text=True,
                        stdin=subprocess.DEVNULL)


# --- the fixture corpus -------------------------------------------------
#
# A handful of files each, not a realistic app: this only needs to exercise
# install/recon/run_checks, not run a real build.

def fixture_greenfield(base: Path) -> Path:
    """Empty. The stage with nothing in it at all, beyond `.git`."""
    d = base / "greenfield"
    d.mkdir(parents=True)
    _git_init(d)
    return d


def fixture_partial(base: Path) -> Path:
    """Some source, some tests, a README -- partially built, not broken."""
    d = base / "partial"
    d.mkdir(parents=True)
    _git_init(d)
    (d / "README.md").write_text("# partial\n", encoding="utf-8")
    (d / "pyproject.toml").write_text(
        "[project]\nname = \"partial\"\nversion = \"0.1.0\"\n", encoding="utf-8")
    (d / "src").mkdir()
    (d / "src" / "app.py").write_text("def add(a, b):\n    return a + b\n",
                                       encoding="utf-8")
    (d / "src" / "util.py").write_text("def noop():\n    pass\n", encoding="utf-8")
    (d / "tests").mkdir()
    (d / "tests" / "test_app.py").write_text(
        "from src.app import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8")
    # Stands in for "the target's pre-existing build/test command" -- read
    # by the objective-27 zero-migration check.
    (d / "check.py").write_text("print('ok')\n", encoding="utf-8")
    return d


def fixture_legacy(base: Path) -> Path:
    """Source with no tests at all -- legacy, not broken; it just predates
    the idea of testing this code."""
    d = base / "legacy"
    d.mkdir(parents=True)
    _git_init(d)
    (d / "README.md").write_text("# legacy\n", encoding="utf-8")
    (d / "pyproject.toml").write_text(
        "[project]\nname = \"legacy\"\nversion = \"0.1.0\"\n", encoding="utf-8")
    (d / "lib").mkdir()
    (d / "lib" / "core.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (d / "lib" / "helpers.py").write_text("def helper():\n    return 2\n",
                                           encoding="utf-8")
    (d / "check.py").write_text("print('ok')\n", encoding="utf-8")
    # Deliberately no tests/ directory at all -- the whole point of this stage.
    return d


def fixture_broken(base: Path) -> Path:
    """Genuinely broken, independent of what toolchain happens to be on the
    machine running this suite: one file with invalid Python syntax, one
    test that always fails."""
    d = base / "broken"
    d.mkdir(parents=True)
    _git_init(d)
    (d / "README.md").write_text("# broken\n", encoding="utf-8")
    (d / "pyproject.toml").write_text(
        "[project]\nname = \"broken\"\nversion = \"0.1.0\"\n", encoding="utf-8")
    (d / "src").mkdir()
    (d / "src" / "bad.py").write_text("def f(:\n    pass\n", encoding="utf-8")
    (d / "tests").mkdir()
    (d / "tests" / "test_fails.py").write_text(
        "def test_never():\n    assert False, 'deliberately broken fixture'\n",
        encoding="utf-8")
    (d / "check.py").write_text("print('ok')\n", encoding="utf-8")
    return d


def fixture_undocumented(base: Path) -> Path:
    """Working source and tests, but no README, CONTRIBUTING, or any other
    doc file at all."""
    d = base / "undocumented"
    d.mkdir(parents=True)
    _git_init(d)
    (d / "pyproject.toml").write_text(
        "[project]\nname = \"undoc\"\nversion = \"0.1.0\"\n", encoding="utf-8")
    (d / "src").mkdir()
    (d / "src" / "app.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    (d / "tests").mkdir()
    (d / "tests" / "test_app.py").write_text(
        "from src.app import main\n\n\ndef test_main():\n    assert main() == 0\n",
        encoding="utf-8")
    (d / "check.py").write_text("print('ok')\n", encoding="utf-8")
    return d


def fixture_go(base: Path) -> Path:
    """A bare non-Python, non-Node stack for objective 25: a `go.mod` and a
    package layout. Nothing here needs `go` installed to compile or run --
    the layout alone is what the objective asks for."""
    d = base / "go-stack"
    d.mkdir(parents=True)
    _git_init(d)
    (d / "go.mod").write_text("module example.com/fixture\n\ngo 1.21\n",
                               encoding="utf-8")
    (d / "main.go").write_text(
        "package main\n\nfunc main() {\n\tprintln(\"ok\")\n}\n", encoding="utf-8")
    (d / "pkg").mkdir()
    (d / "pkg" / "lib.go").write_text(
        "package pkg\n\nfunc Add(a, b int) int {\n\treturn a + b\n}\n",
        encoding="utf-8")
    return d


STAGES = {
    "greenfield": fixture_greenfield,
    "partial": fixture_partial,
    "legacy": fixture_legacy,
    "broken": fixture_broken,
    "undocumented": fixture_undocumented,
}


def all_paths(root: Path) -> set[str]:
    """Every file's path relative to `root`, `.git` excluded."""
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


def run_check_py(d: Path) -> tuple[int, str]:
    """(returncode, stdout). A missing `check.py` returns nonzero with EMPTY
    stdout, which is why the caller must not compare stdout alone -- two
    empty strings are equal, and a comparison that only checked stdout
    "passed" silently when the command did not run at all. Found by seeding
    exactly that case before trusting this check."""
    proc = subprocess.run(
        [sys.executable, "check.py"], cwd=str(d),
        capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    return proc.returncode, proc.stdout.strip()


def main() -> int:
    base = Path(tempfile.mkdtemp()) / "target-matrix"
    base.mkdir(parents=True)

    fixtures: dict[str, Path] = {}
    for name, builder in {**STAGES, "go-stack": fixture_go}.items():
        fixtures[name] = builder(base)
    check(f"{len(fixtures)} fixture(s) built",
          all((fixtures[n] / ".git").is_dir() for n in fixtures),
          str([n for n in fixtures if not (fixtures[n] / ".git").is_dir()]))

    # --- objective 27's "before" snapshot -- MUST be captured before any
    # install runs, or it is not a snapshot of the pre-install state at all.
    pre_paths = {name: all_paths(d) for name, d in fixtures.items()}
    pre_rc, pre_check_output = run_check_py(fixtures["partial"])
    check("the fixture's pre-existing command runs BEFORE install (sanity)",
          pre_rc == 0 and pre_check_output == "ok",
          f"rc={pre_rc} stdout={pre_check_output!r} -- if this is not a real "
          f"baseline, the before/after comparison below cannot mean anything")

    # --- objective 15: install, recon, run_checks -- no crash, non-empty facts
    #
    # Only ONE stage actually EXECUTES its resolved fast-tier checks
    # (`pc.run_checks`) end to end -- measured at ~3.2s per Python fixture,
    # almost all of it real `mypy`/`ruff` subprocess startup once `install.py`
    # seeds `ruff.toml`/`mypy.ini` into a fixture with real `.py` files. Doing
    # that for all 4 Python stages would have added ~12-13s to a suite that
    # joins the FAST tier, which gates every auto-commit -- against this
    # repo's own S1 "make every turn cheap" discipline. `resolve_checks` (the
    # detection half `run_checks` wraps) costs a few milliseconds and is run
    # for every stage, which is what proves "no crash" for the other four;
    # `pc.run_checks` is exercised fully on `broken` -- the stage whose whole
    # point is to be a hard case for the fast tier to survive.
    DEEP_RUN_STAGE = "broken"
    stage_results: dict[str, bool] = {}
    stage_detail: dict[str, str] = {}
    recon_facts: dict[str, dict] = {}
    resolved_checks: dict[str, list] = {}
    for name in STAGES:
        d = fixtures[name]
        try:
            actions, _warnings = inst.plan(d)
            inst.apply(d, actions)
            facts = recon.gather(d)
            checks_here, _disabled = pc.resolve_checks(d, pc.FAST_KINDS)
            if name == DEEP_RUN_STAGE:
                ok, detail, _ran_test = pc.run_checks(d, kinds=pc.FAST_KINDS)
                run_note = f"run_checks ok={ok} ({detail})"
            else:
                run_note = "resolve_checks only (see DEEP_RUN_STAGE note above)"
            recon_facts[name] = facts
            resolved_checks[name] = checks_here
            stage_results[name] = True
            stage_detail[name] = run_note
        except Exception as exc:  # noqa: BLE001 -- a crash IS the failure this counts
            stage_results[name] = False
            stage_detail[name] = f"{type(exc).__name__}: {exc}"

    passed = sum(1 for v in stage_results.values() if v)
    check(f"stage-fixture pass rate: {passed}/{len(STAGES)}",
          passed == len(STAGES),
          "; ".join(f"{n}: {stage_detail[n]}" for n in STAGES if not stage_results[n]))

    for name in STAGES:
        if name in recon_facts:
            f = recon_facts[name]
            check(f"recon returns a non-empty map for '{name}'",
                  bool(f) and {"root", "stack", "tests", "git", "units"} <= set(f),
                  str(sorted(f.keys())) if f else "empty")

    # --- objective 16a: recon reports REAL structure, not a constant
    expected_languages = {
        "greenfield": set(),
        "partial": {"python"},
        "legacy": {"python"},
        "broken": {"python"},
        "undocumented": {"python"},
    }
    for name, expect in expected_languages.items():
        if name not in recon_facts:
            continue
        got = set(recon_facts[name]["stack"]["languages"])
        check(f"recon detects real languages for '{name}': {sorted(expect) or 'none'}",
              got == expect, f"got {sorted(got)}")

    # --- objective 16b: zero check-leakage from this repo's own gating list
    own_project_checks = json.loads(
        (ROOT / ".claude" / "project-checks.json").read_text(encoding="utf-8"))
    own_test_cmds = set(own_project_checks.get("test") or [])

    leaked = {}
    for name in STAGES:
        if name not in resolved_checks:
            continue
        cmds = {cmd for _kind, cmd in resolved_checks[name]}
        overlap = own_test_cmds & cmds
        if overlap:
            leaked[name] = overlap
    check("no fixture resolves any of this repo's own gating test commands",
          not leaked, str(leaked))

    # Proof the leak-check has teeth: resolving THIS repo's own checks against
    # ITSELF must intersect `own_test_cmds`, or the fixture-side assertion
    # above would be vacuously true and prove nothing.
    root_checks, _ = pc.resolve_checks(ROOT, pc.FAST_KINDS)
    root_cmds = {cmd for _kind, cmd in root_checks}
    check("the leak-check can actually fail (seeded: resolving against ROOT itself)",
          bool(own_test_cmds & root_cmds),
          "if this finds no overlap either, the assertion above is vacuous")

    # --- objective 25: technology-agnostic -- the Go-stack fixture
    go_dir = fixtures["go-stack"]
    try:
        go_actions, go_warnings = inst.plan(go_dir)
        inst.apply(go_dir, go_actions)
        go_facts = recon.gather(go_dir)
        go_ok = True
    except Exception as exc:  # noqa: BLE001
        go_warnings = []
        go_facts = {}
        go_ok = False
        check("go-stack fixture installs without crashing", False, f"{type(exc).__name__}: {exc}")

    if go_ok:
        check("go-stack fixture installs without crashing", True)
        check("no ruff.toml seeded into a non-Python target",
              not (go_dir / "ruff.toml").is_file())
        check("no mypy.ini seeded into a non-Python target",
              not (go_dir / "mypy.ini").is_file())
        check("...and both skips are reported, never silent",
              any("ruff.toml" in w for w in go_warnings)
              and any("mypy.ini" in w for w in go_warnings),
              str(go_warnings))
        check("recon detects the real stack: go",
              "go" in go_facts.get("stack", {}).get("languages", []),
              str(go_facts.get("stack")))

    # --- objective 27: progressively adoptable -- zero-migration boolean
    zero_migration: dict[str, bool] = {}
    for name in STAGES:
        if name not in recon_facts:
            continue
        post = all_paths(fixtures[name])
        zero_migration[name] = pre_paths[name] <= post
        check(f"zero-migration: '{name}' -- no pre-existing file moved or renamed",
              zero_migration[name],
              str(sorted(pre_paths[name] - post))[:200])

    post_rc, post_check_output = run_check_py(fixtures["partial"])
    # `post_check_output == pre_check_output` alone is not this check -- a
    # missing check.py returns rc=1 with EMPTY stdout both before and after,
    # and two empty strings compare equal. Found live by seeding exactly
    # that (deleting check.py before the "before" snapshot) and watching this
    # assertion pass anyway; `pre_rc == 0`/`post_rc == 0` close it.
    check("the target's own pre-existing command runs unchanged after install",
          post_rc == 0 and post_check_output == pre_check_output == "ok",
          f"before=(rc={pre_rc}, {pre_check_output!r}) "
          f"after=(rc={post_rc}, {post_check_output!r})")

    shutil.rmtree(base.parent, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} failed: {', '.join(failures)}")
        return 1
    print("All target-matrix tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

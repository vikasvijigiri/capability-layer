#!/usr/bin/env python3
"""Tests for _projectchecks.py and the credential patterns it gates alongside.

What makes an unattended commit acceptable is that something could have failed.
So the two things asserted hardest here are:

  1. Detection actually finds a real project's checks -- `npm test`,
     `tsc --noEmit`, `pytest`, `cargo test` -- rather than only this repo's
     `tools/test_*.py`, which is what it looked for until 2026-08-02.
  2. `run_checks` reports **whether a test ran** separately from whether
     everything passed. Those are the same boolean and different facts, and
     conflating them is how the gate stops guarding without anyone noticing.

Detection cases build throwaway project trees in temp directories. Nothing here
runs a real `npm` or `cargo`.

Run: python tools/test_project_checks.py
"""
from __future__ import annotations

import importlib.util
import json
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
    # Not type-checker appeasement: a mistyped path returns None here and fails
    # two lines down as `NoneType has no attribute loader`, which reads like a
    # bug in the module under test rather than a wrong path in this file.
    assert spec is not None, f"no import spec for {rel}"
    assert spec.loader is not None, f"no loader for {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


pc = load(".claude/hooks/_projectchecks.py", "projectchecks")
hl = load(".claude/hooks/_hooklib.py", "hooklib_pc")


def tree(files: dict) -> Path:
    """A throwaway project. Values are file contents; dirs are created."""
    d = Path(tempfile.mkdtemp())
    for rel, body in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return d


def kinds(root) -> set:
    return {k for k, _ in pc.detect_checks(root)}


def commands(root) -> str:
    return " | ".join(c for _, c in pc.detect_checks(root))


# --- detection: the shapes a real product actually has ----------------------

node = tree({"package.json": json.dumps(
    {"scripts": {"test": "vitest", "lint": "eslint .", "build": "next build"}}),
    "package-lock.json": "{}", "tsconfig.json": "{}"})
check("a node app detects the full set",
      kinds(node) == {"test", "lint", "typecheck", "build", "audit"}, str(kinds(node)))
check("...including a build, which lint and tests cannot substitute for",
      "npm run build" in commands(node), commands(node))
check("...and a vulnerability audit at high severity",
      "npm audit --audit-level=high" in commands(node), commands(node))
check("...and uses npm when package-lock.json is the lockfile",
      "npm test" in commands(node), commands(node))
check("...and falls back to tsc --noEmit from tsconfig.json alone",
      "tsc --noEmit" in commands(node), commands(node))

pnpm = tree({"package.json": json.dumps({"scripts": {"test": "vitest"}}),
             "pnpm-lock.yaml": ""})
check("the lockfile picks the package manager, not a guess",
      "pnpm test" in commands(pnpm), commands(pnpm))

py = tree({"pyproject.toml": "[project]\nname='x'\n", "ruff.toml": "",
           "mypy.ini": "[mypy]\n"})
check("a python app detects pytest, ruff, mypy and an audit",
      kinds(py) == {"test", "lint", "typecheck", "audit"}, str(kinds(py)))

# --- every Python tool runs as `{py} -m`, never bare.
#
# Found 2026-08-03 by porting this harness into a fresh repo: `pytest -q` was
# reported "not installed" seconds after `python -m pytest` ran a passing suite,
# because the package was importable but had no console script. The worse case
# is silent: a bare name can resolve to a different interpreter's tool than the
# one running the checks.
PY_TOOLS = ("pytest", "ruff", "mypy", "pip_audit", "pip-audit")
for _kind, _cmd in pc.detect_checks(py) + pc.detect_checks(ROOT):
    _first = _cmd.split()[0].strip('"')
    if any(_first == t or _first.endswith(f"/{t}") or _first.endswith(f"\\{t}")
           for t in PY_TOOLS):
        check(f"python tool invoked bare, not via -m: {_cmd}", False,
              "needs a console script on PATH, and may pick another interpreter")
check("no detected Python tool is invoked bare", True)
check("...with pytest as the test command", "pytest -q" in commands(py))
check("...ruff as the linter", "ruff check" in commands(py))
check("...and mypy as the typechecker", "mypy" in commands(py))

# A config file is what turns each on, so its absence must turn it off.
py_bare = tree({"pyproject.toml": "[project]\nname='x'\n"})
check("no ruff.toml means no lint", "lint" not in kinds(py_bare))
check("no mypy.ini means no typecheck", "typecheck" not in kinds(py_bare))

# What resolves HERE depends on which config files this repo has, so asserting a
# fixed set makes the suite a statement about one repo. It used to demand all
# three, and `install.py` began copying this file to targets on 2026-08-04 -- a
# fresh repo has no linter, resolves `test` alone, and failed a suite that was
# describing somewhere else. The portable invariant is the implication: a config
# file present means its kind resolves, and `test` resolves wherever tests exist.
_resolved = {k for k, _ in pc.resolve_checks(ROOT)[0]}
_expected = {"test"} if list((ROOT / "tools").glob("test_*.py")) else set()
if (ROOT / "ruff.toml").is_file() or (ROOT / ".ruff.toml").is_file():
    _expected.add("lint")
if (ROOT / "mypy.ini").is_file() or (ROOT / "setup.cfg").is_file():
    _expected.add("typecheck")
check("every fast kind this repo has config for actually resolves",
      _expected <= _resolved,
      f"expected at least {sorted(_expected)}, resolved {sorted(_resolved)}")


# --- the two tiers -----------------------------------------------------------
#
# The split is what lets a build and a browser suite exist at all: at per-turn
# cost they would be switched off within a day, and a gate nobody runs is worse
# than no gate because it still reads as coverage.

check("fast and slow tiers do not overlap",
      not (set(pc.FAST_KINDS) & set(pc.SLOW_KINDS)))
check("ALL_KINDS is exactly the union",
      set(pc.ALL_KINDS) == set(pc.FAST_KINDS) | set(pc.SLOW_KINDS))
check("the per-turn tier holds no slow check",
      all(k in pc.FAST_KINDS for k, _ in pc.resolve_checks(ROOT, pc.FAST_KINDS)[0]))

e2e_tree = tree({"playwright.config.ts": "export default {}\n"})
check("a playwright config detects an e2e check",
      kinds(e2e_tree) == {"e2e"} and "playwright test" in commands(e2e_tree),
      commands(e2e_tree))
check("e2e is slow-tier, never per-turn",
      "e2e" in pc.SLOW_KINDS and "e2e" not in pc.FAST_KINDS)
check("a slow-tier resolve finds it",
      any(k == "e2e" for k, _ in pc.resolve_checks(e2e_tree, pc.SLOW_KINDS)[0]))
check("a fast-tier resolve does not",
      not pc.resolve_checks(e2e_tree, pc.FAST_KINDS)[0])


# --- migrations are never auto-committed -------------------------------------
#
# The least reversible thing a product contains, and the one no suite proves.

MIGRATIONS = [
    ("prisma/migrations/001_init/migration.sql", True),
    ("api/alembic/versions/abc123.py", True),
    ("db/migrate/20240101_add_users.rb", True),
    ("sup" + "abase/migrations/0001.sql", True),
    ("schema.sql", True),
    ("src/app.py", False),
    ("docs/migrations-guide.md", False),
    ("README.md", False),
]
for rel, want in MIGRATIONS:
    got = bool(hl.migration_paths([rel]))
    check(f"migration {rel} detected={want}", got is want, f"got {got}")


# --- a configured tool that is not installed must skip, never fail ----------
#
# Otherwise the first fresh clone refuses every commit until someone installs a
# linter, and the person who hits that is never the person who wrote the config.

check("a missing python module is detected",
      pc.tool_missing("python -m definitely_not_installed check"))
check("a missing executable is detected",
      pc.tool_missing("definitely-not-a-real-binary --version"))
check("an installed module is not flagged",
      not pc.tool_missing("python -m json.tool"))

ghost = tree({".claude/project-checks.json": json.dumps(
    {"test": "python -m no_such_test_runner", "lint": False})})
ok, detail, ran_test = pc.run_checks(ghost)
check("an uninstalled tool skips rather than failing", ok, detail)
check("...and says which one, by name",
      "not installed" in detail and "no_such_test_runner" in detail, detail)
check("...and still reports that no test ran", ran_test is False)

# --- the table is language-agnostic; each ecosystem is a row, not a code path
ECOSYSTEMS = [
    ("rust",   {"Cargo.toml": "[package]\nname='x'\n"},
     {"test", "lint", "build", "audit"}, "cargo test"),
    ("go",     {"go.mod": "module x\n"},
     {"test", "lint", "build", "audit"}, "go test ./..."),
    ("maven",  {"pom.xml": "<project/>\n"},                       {"test"},         "mvn"),
    ("gradle", {"build.gradle.kts": "plugins {}\n"},              {"test"},         "gradle"),
    ("ruby",   {"Rakefile": "task :test\n", ".rubocop.yml": ""},  {"test", "lint"}, "rubocop"),
    ("php",    {"phpunit.xml": "<phpunit/>\n"},                   {"test"},         "phpunit"),
    ("elixir", {"mix.exs": "defmodule X do\nend\n"},              {"test", "lint"}, "mix test"),
    ("deno",   {"deno.json": "{}\n"},          {"test", "lint", "typecheck"},       "deno test"),
    ("dotnet", {"App.csproj": "<Project/>\n"},                    {"test"},         "dotnet test"),
]
for label, files, want_kinds, want_cmd in ECOSYSTEMS:
    t = tree(files)
    check(f"{label} detects {sorted(want_kinds)}", kinds(t) == want_kinds, str(kinds(t)))
    check(f"...with {want_cmd!r} among its commands", want_cmd in commands(t), commands(t))

# `make` is the closest thing to a universal interface, so it is detected -- but
# only for targets that exist. A Makefile with no `test:` target must not produce
# a `make test` command that fails for everyone.
mk = tree({"Makefile": "build:\n\tcc x.c\n\ntest:\n\t./run\n"})
check("make detects only the targets that exist",
      kinds(mk) == {"test"} and "make test" in commands(mk), commands(mk))
mk_none = tree({"Makefile": "build:\n\tcc x.c\n"})
check("a Makefile with no test target detects nothing",
      pc.detect_checks(mk_none) == [], str(pc.detect_checks(mk_none)))

# Two markers meaning the same tool must not run it twice.
dup = tree({"pyproject.toml": "[project]\nname='x'\n", "pytest.ini": "[pytest]\n"})
check("duplicate markers do not duplicate the command",
      sum(1 for _, c in pc.detect_checks(dup) if c.endswith("-m pytest -q")) == 1,
      str(pc.detect_checks(dup)))

empty = tree({"README.md": "# hi\n"})
check("a project with no markers detects nothing", pc.detect_checks(empty) == [])

check("this repo still detects its own suites",
      any("test_hooks.py" in c for _, c in pc.detect_checks(ROOT)))


# --- config overrides detection ---------------------------------------------

over = tree({"package.json": json.dumps({"scripts": {"test": "vitest"}}),
             ".claude/project-checks.json": json.dumps(
                 {"test": "npm run test:fast", "lint": False})})
resolved, disabled = pc.resolve_checks(over)
check("a configured command replaces the detected one",
      [c for k, c in resolved if k == "test"] == ["npm run test:fast"], str(resolved))
check("false disables a check as a stated decision", "lint" in disabled)

check("a missing config file is not an error", pc.load_config(empty) == {})
broken = tree({".claude/project-checks.json": "{ not json"})
check("a malformed config falls back to detection rather than crashing",
      pc.load_config(broken) == {})


# --- the load-bearing distinction: passed vs nothing ran --------------------

ok, detail, ran_test = pc.run_checks(empty)
check("a project with no checks does not fail", ok)
check("...but reports that no test ran", ran_test is False, f"ran_test={ran_test}")
check("...and says so in words", "no checks detected" in detail, detail)

green = tree({"tools/test_ok.py": "print('fine')\n"})
ok, detail, ran_test = pc.run_checks(green)
check("a passing suite is green and counts as a test", ok and ran_test, detail)

# --- a failing check must report WHY, not merely what was printed last -------
#
# The shape that defeated the old `(stdout or stderr)[-1]`: a suite whose checks
# all print OK to stdout, which then dies during teardown with a traceback on
# stderr. Reported as `OK: ...`, it is a red build whose stated cause is a
# passing check -- and on 2026-08-07 that cost a full reproduction to diagnose.

teardown = tree({"tools/test_teardown.py":
                 "import sys\n"
                 "print('OK: every check passed')\n"
                 "print('OK: bootstrap whitelist is exactly the six known docs')\n"
                 "sys.stderr.write('PermissionError: [WinError 5] Access is denied\\n')\n"
                 "sys.exit(1)\n"})
ok, detail, _ = pc.run_checks(teardown)
check("a suite that dies after printing OK is still red", not ok, detail)
check("...and the reported reason is the error, not the last OK line",
      "PermissionError" in detail, detail)
check("...so no failure is ever explained by a passing check",
      not detail.rstrip().endswith("OK: bootstrap whitelist is exactly the six known docs"),
      detail)

marker_only = tree({"tools/test_marker.py":
                    "import sys\n"
                    "print('OK: a failing suite is red')\n"
                    "print('FAIL: the real problem')\n"
                    "print('2 finding(s).')\n"
                    "sys.exit(1)\n"})
ok, detail, _ = pc.run_checks(marker_only)
check("with no stderr, an explicit FAIL line is preferred over the last line",
      "the real problem" in detail, detail)
check("...and an OK line mentioning the word 'failing' is not mistaken for one",
      "a failing suite is red" not in detail, detail)

red = tree({"tools/test_bad.py": "import sys\nprint('boom')\nsys.exit(1)\n"})
ok, detail, ran_test = pc.run_checks(red)
check("a failing suite is red", not ok, detail)
check("...and the failure names the command", "test_bad.py" in detail, detail)

disabled_tree = tree({"pyproject.toml": "[project]\nname='x'\n",
                      ".claude/project-checks.json": json.dumps({"test": False})})
ok, detail, ran_test = pc.run_checks(disabled_tree)
check("disabling tests is honoured and reported",
      ok and ran_test is False and "disabled" in detail, detail)


# --- which changes need a test to have run ----------------------------------

check("a code change needs a test", pc.changed_includes_code(["src/app.tsx"]))
check("a python change needs a test", pc.changed_includes_code(["api/main.py"]))
check("a prose-only change does not",
      not pc.changed_includes_code(["README.md", "docs/x.md", "LOG.md"]))
check("a lockfile alone does not",
      not pc.changed_includes_code(["package-lock.json", ".gitignore"]))
check("a mixed change does", pc.changed_includes_code(["README.md", "src/a.go"]))


# --- credentials, both axes -------------------------------------------------

PATHS = [(".env", True), ("./.env", True), ("app/.env.local", True),
         (".env.example", False), (".env.template", False),
         ("keys/id_rsa", True), ("certs/server.pem", True), ("cfg/.npmrc", True),
         ("infra/terraform.tfvars", True), ("db.sqlite3", True),
         ("src/app.py", False), ("docs/x.md", False)]
for rel, want in PATHS:
    check(f"path {rel} blocked={want}", hl.secret_path_hit(rel) is want)

# Every positive fixture is assembled at runtime rather than written as one
# literal. This file is scanned by the same patterns it tests, so a contiguous
# example credential here makes the repo permanently uncommittable -- which is
# exactly what happened on 2026-08-03 before these were split. `test_hooks.py`
# documents the identical trap for `AKIA`.
CONTENT = [("postgres" + "://user" + ":pw@host/db", True, "DSN with inline creds"),
           ("sk_live_" + "a" * 24, True, "stripe live key"),
           ("eyJ" + "hbGciOiJIUzI1NiJ9." + "eyJ" + "zdWIiOiIxIn0.sig", True, "jwt"),
           ("xoxb" + "-123456789012-abcdefghijkl", True, "slack token"),
           ("AIza" + "B" * 35, True, "google api key"),
           ("gh" + "p_" + "A" * 36, True, "github pat"),
           ("import os\nprint('hello')", False, "ordinary source"),
           ("https://example.com/path", False, "a plain url"),
           ("redis://localhost:6379/0", False, "a DSN with no credentials")]
for text, want, label in CONTENT:
    got = any(p.search(text) for p in hl.SECRET_PATTERNS)
    check(f"content: {label} flagged={want}", got is want, text[:40])

# --- the repo must not trip its own scanner --------------------------------
#
# The auto-commit refuses on any finding, so a self-match does not merely add
# noise: it blocks every commit until someone works out why. Catching it here
# fails loudly at test time instead.
_self_hits = hl.scan_for_secrets(
    [str(p.relative_to(ROOT)).replace("\\", "/")
     for p in list(ROOT.glob("tools/*.py")) + list((ROOT / ".claude/hooks").rglob("*.py"))],
    ROOT)
check("this repo's own source does not match the credential patterns",
      _self_hits == [], f"self-matching: {_self_hits}")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All project-check tests passed")

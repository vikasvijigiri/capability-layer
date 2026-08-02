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
check("a node app detects test, lint and typecheck",
      kinds(node) == {"test", "lint", "typecheck"}, str(kinds(node)))
check("...and uses npm when package-lock.json is the lockfile",
      "npm test" in commands(node), commands(node))
check("...and falls back to tsc --noEmit from tsconfig.json alone",
      "tsc --noEmit" in commands(node), commands(node))

pnpm = tree({"package.json": json.dumps({"scripts": {"test": "vitest"}}),
             "pnpm-lock.yaml": ""})
check("the lockfile picks the package manager, not a guess",
      "pnpm test" in commands(pnpm), commands(pnpm))

py = tree({"pyproject.toml": "[project]\nname='x'\n", "ruff.toml": ""})
check("a python app detects pytest and ruff",
      kinds(py) == {"test", "lint"}, str(kinds(py)))
check("...with pytest as the test command", "pytest -q" in commands(py))

rust = tree({"Cargo.toml": "[package]\nname='x'\n"})
check("a rust crate detects cargo test and clippy",
      kinds(rust) == {"test", "lint"} and "cargo test" in commands(rust))

go = tree({"go.mod": "module x\n"})
check("a go module detects go test and vet",
      kinds(go) == {"test", "lint"} and "go test ./..." in commands(go))

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

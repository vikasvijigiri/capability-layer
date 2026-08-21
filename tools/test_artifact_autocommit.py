"""Tests for stop-finalization/06-artifact-autocommit.py -- the only hook that commits.

Its commits are made from a subprocess, so they never pass through `PreToolUse`
and get none of the gates a model-issued `git commit` gets. The checks it runs
inline are therefore the only checks those commits ever receive, and every one is
asserted here.

Behaviour cases run against a throwaway git repo in a temp directory -- never
this one -- and assert on real `git log` / `git status` output rather than on the
hook's own report. A hook that reports success having done nothing is precisely
the failure this file exists to catch.

Run: python tools/test_artifact_autocommit.py
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
HOOK = ROOT / ".claude" / "hooks" / "stop-finalization" / "06-artifact-autocommit.py"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load():
    spec = importlib.util.spec_from_file_location("autocommit", HOOK)
    # Real asserts, not type-checker appeasement: a mistyped path returns None
    # and fails two lines down as `NoneType has no attribute loader`, which reads
    # like a bug in the hook rather than a wrong path here.
    assert spec is not None, f"no import spec for {HOOK}"
    assert spec.loader is not None, f"no loader for {HOOK}"
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
    run(tmp, "init", "-q", "-b", "work")
    run(tmp, "config", "user.email", "t@example.com")
    run(tmp, "config", "user.name", "T")
    run(tmp, "commit", "-q", "--allow-empty", "-m", "base")


def write(tmp: Path, rel: str, body: str) -> None:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def commit_count(tmp: Path) -> int:
    out = run(tmp, "log", "--oneline")
    return len([ln for ln in out.splitlines() if ln.strip()])


os.environ.setdefault("HOOK_PAYLOAD", "{}")
mod = load()

# ---------------------------------------------------------------- re-entry guard
#
# The bug this prevents was found by a two-minute timeout, not by an error:
# test_hooks.py fires the whole post-run event -> this hook -> run_suites() ->
# test_hooks.py, unbounded. A hang and a pass look identical from outside, which
# is the exact failure mode CLAUDE.md warns about for hooks.

check("a re-entry flag exists", bool(getattr(mod, "REENTRY_FLAG", "")))
check("run_suites propagates the flag to every check it runs",
      "REENTRY_FLAG" in HOOK.read_text(encoding="utf-8"),
      "checks would re-enter this hook and recurse")

# With the flag set, main() must do nothing at all.
os.environ[mod.REENTRY_FLAG] = "1"
_before = mod.changed_paths
mod.changed_paths = lambda *_a, **_k: (_ for _ in ()).throw(
    AssertionError("main() reached changed_paths() under the re-entry flag"))
try:
    mod.main()
    check("main() no-ops under the re-entry flag", True)
except AssertionError as exc:
    check("main() no-ops under the re-entry flag", False, str(exc))
finally:
    mod.changed_paths = _before

# Everything below drives main() against a TEMP repo, so the production guard is
# lifted deliberately. Leaving it set made this suite fail 10 assertions, which
# made the suite gate red, which meant the hook could never commit -- the guard
# disabling the thing under test is a real failure mode, found on 2026-08-02.
os.environ.pop(mod.REENTRY_FLAG, None)

# ------------------------------------------------------- pure gates, no git needed

_probe = ROOT / "_autocommit_secret_probe.txt"
# Assembled at runtime: 01-secret-scan.py scans this file too, and a literal
# AKIA + 16 chars here would make the repo permanently uncommittable.
_probe.write_text('aws_key = "' + "AKIA" + 'ABCDEFGHIJKLMNOP"\n', encoding="utf-8")
try:
    check("a planted credential is caught",
          _probe.name in mod.scan_for_secrets([_probe.name], ROOT))
finally:
    _probe.unlink(missing_ok=True)

check("ordinary source is not flagged",
      mod.scan_for_secrets(["tools/run_hook.py"], ROOT) == [])
check("an unreadable path is skipped rather than crashed on",
      mod.scan_for_secrets(["does/not/exist.py"], ROOT) == [])

check("main and master are protected",
      {"main", "master"} <= mod.PROTECTED_BRANCHES)
check("the size ceiling has a sane default",
      isinstance(mod.DEFAULT_MAX_FILES, int) and 0 < mod.DEFAULT_MAX_FILES <= 100)
check("settings.json is never auto-committed",
      ".claude/settings.json" in mod.NEVER_AUTO)
check("settings.local.json is never auto-committed",
      ".claude/settings.local.json" in mod.NEVER_AUTO)

_msg = mod.build_message(["a/b.py", "a/c.py", "tools/d.py"], "6 suite(s) green")
_subject = _msg.splitlines()[0]
check("message is marked as a checkpoint", _subject.startswith("wip:"), _subject)
check("subject stays within 72 chars", len(_subject) <= 72, f"{len(_subject)}")
check("message carries the verification evidence", "6 suite(s) green" in _msg)
check("message lists every path",
      all(f"- {p}" in _msg for p in ("a/b.py", "a/c.py", "tools/d.py")))
check("many areas still yield a short subject",
      len(mod.build_message([f"a{i}/f.py" for i in range(20)], "g").splitlines()[0]) <= 72)
# CLAUDE.md forbids AI attribution in git history, and nobody reads this message
# before it lands.
check("generated message carries no AI attribution",
      not any(p.search(_msg) for p in mod.AI_ATTRIBUTION_PATTERNS))
check("attribution patterns would catch a planted trailer",
      any(p.search(_msg + "\nCo-authored-by: Claude <n@a>")
          for p in mod.AI_ATTRIBUTION_PATTERNS))

# Delegated to _projectchecks now, and covered in depth by
# tools/test_project_checks.py. What matters here is the wiring: run_suites must
# return the three-value shape the gates below depend on.
#
# Against an EMPTY temp root, never the real one. The re-entry flag is popped
# above so that main() can be driven, which means a run_suites() call aimed at
# this repo would run this very suite, which pops the flag, which calls
# run_suites()... The guard protects the hook's own path; it cannot protect a
# test that deliberately steps around it. Found by a 120s timeout on 2026-08-03.
_saved_root = mod.REPO_ROOT
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as _empty:
    mod.REPO_ROOT = Path(_empty)
    _probe = mod.run_suites()
mod.REPO_ROOT = _saved_root
check("run_suites returns (ok, detail, ran_test)",
      isinstance(_probe, tuple) and len(_probe) == 3, str(_probe)[:80])
check("...and reports no test ran when nothing is detected",
      _probe[0] is True and _probe[2] is False, str(_probe)[:80])

# ------------------------------------------------------------- behaviour, on git

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    tmp = Path(d)
    new_repo(tmp)
    mod.REPO_ROOT = tmp
    # A real, detectable, passing suite. Without one, gate 4b correctly refuses
    # every commit containing code, and the happy path below could not exist --
    # which is the whole point of that gate.
    write(tmp, "tools/test_smoke.py", "print('smoke ok')\n")
    run(tmp, "add", "-A")
    run(tmp, "commit", "-q", "-m", "add suite")
    mod.load_payload = lambda: {"stop_hook_active": False}

    base = commit_count(tmp)

    # --- nothing changed: silent, no commit
    check("silent with a clean tree", emit(mod) == {})
    check("...and no commit was made", commit_count(tmp) == base)

    # --- the happy path: code IS committed now, unlike the prose-only version
    write(tmp, "src/app.py", "print(1)\n")
    write(tmp, "LOG.md", "entry\n")
    result = emit(mod)
    check("fires on ordinary changed files", "hookSpecificOutput" in result)
    check("...and actually commits", commit_count(tmp) == base + 1)
    committed = sorted(run(tmp, "show", "--name-only", "--format=", "HEAD").split())
    check("commits code as well as prose", committed == ["LOG.md", "src/app.py"],
          f"got {committed}")
    check("subject marks it as an unreviewed checkpoint",
          run(tmp, "log", "-1", "--format=%s").startswith("wip:"))
    check("working tree is clean afterwards", run(tmp, "status", "--porcelain") == "")

    # --- a protected branch is refused
    run(tmp, "checkout", "-q", "-b", "main")
    write(tmp, "src/app.py", "print(2)\n")
    result = emit(mod)
    at = commit_count(tmp)
    check("refuses on a protected branch",
          "protected branch" in json.dumps(result), json.dumps(result)[:120])
    check("...and commits nothing there", commit_count(tmp) == at)
    run(tmp, "checkout", "-q", "work")
    run(tmp, "checkout", "-q", "--", ".")

    # --- a credential blocks the whole commit, not just that file
    at = commit_count(tmp)
    write(tmp, "src/ok.py", "x = 1\n")
    write(tmp, "src/leak.py", 'token = "' + "AKIA" + 'ABCDEFGHIJKLMNOP"\n')
    result = emit(mod)
    check("refuses when a credential is present",
          "REFUSED" in json.dumps(result), json.dumps(result)[:160])
    check("...and commits nothing at all, not even the clean file",
          commit_count(tmp) == at)
    check("...and leaves the index untouched",
          run(tmp, "diff", "--cached", "--name-only") == "")
    (tmp / "src" / "leak.py").unlink()

    # --- too large to be a checkpoint
    at = commit_count(tmp)
    for i in range(mod.DEFAULT_MAX_FILES + 2):
        write(tmp, f"bulk/f{i}.py", f"n = {i}\n")
    result = emit(mod)
    check("refuses a change too large to be a checkpoint",
          "max_files" in json.dumps(result), json.dumps(result)[:160])
    check("...and commits nothing", commit_count(tmp) == at)
    for i in range(mod.DEFAULT_MAX_FILES + 2):
        (tmp / "bulk" / f"f{i}.py").unlink()

    # --- red suites stop the commit
    at = commit_count(tmp)
    write(tmp, "src/ok2.py", "y = 2\n")
    _saved = mod.run_suites
    try:
        mod.run_suites = lambda: (False, "test_x.py: 1 failed", True)
        result = emit(mod)
        check("refuses while the suites are red",
              "red" in json.dumps(result), json.dumps(result)[:160])
        check("...and commits nothing", commit_count(tmp) == at)
    finally:
        mod.run_suites = _saved

    # --- settings.json is held out even when it changed
    at = commit_count(tmp)
    write(tmp, ".claude/settings.json", '{"hooks": {}}\n')
    write(tmp, "src/ok3.py", "z = 3\n")
    emit(mod)
    committed = run(tmp, "show", "--name-only", "--format=", "HEAD").split()
    check("commits the rest of the turn", "src/ok3.py" in committed)
    check("...but never settings.json", ".claude/settings.json" not in committed)
    # -uall, not the default: git collapses an untracked directory to `.claude/`
    # and the assertion would pass or fail on that formatting rather than on the
    # file. `_hooklib.changed_paths` documents the same trap.
    check("...which is left uncommitted in the tree",
          ".claude/settings.json" in run(tmp, "status", "--porcelain", "-uall"))

# --- gate 4b: code with nothing that could have failed
#
# The gate that makes unattended committing mean anything. A repo with no test
# command commits prose freely and refuses code, because "all checks passed" and
# "no check ran" are the same boolean and completely different facts.
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d2:
    tmp2 = Path(d2)
    new_repo(tmp2)
    mod.REPO_ROOT = tmp2
    base2 = commit_count(tmp2)

    write(tmp2, "README.md", "# docs\n")
    emit(mod)
    check("prose commits fine with no test command",
          commit_count(tmp2) == base2 + 1)

    write(tmp2, "src/api.py", "def add(a, b):\n    return a + b\n")
    result = emit(mod)
    check("code is REFUSED when no test check ran",
          "REFUSED" in json.dumps(result) and "no test check" in json.dumps(result),
          json.dumps(result)[:180])
    check("...and nothing was committed", commit_count(tmp2) == base2 + 1)

    # Saying "this project has no tests" out loud is a decision, and it unblocks.
    write(tmp2, ".claude/project-checks.json", json.dumps({"test": False}))
    emit(mod)
    check('...until `"test": false` states it deliberately',
          commit_count(tmp2) == base2 + 2)

    # --- gate 2b: a schema migration is never auto-committed
    #
    # The least reversible thing a product contains. `git revert` restores code;
    # nothing restores a dropped column, and no suite proves an ALTER TABLE was
    # the right idea.
    at2 = commit_count(tmp2)
    write(tmp2, "prisma/migrations/001_init/migration.sql",
          "ALTER TABLE users DROP COLUMN email;\n")
    write(tmp2, "src/unrelated.py", "q = 1\n")
    result = emit(mod)
    check("a schema migration is REFUSED",
          "REFUSED" in json.dumps(result) and "migration" in json.dumps(result),
          json.dumps(result)[:180])
    check("...and nothing else in the turn slips through with it",
          commit_count(tmp2) == at2)

# --- the diagnose loop -------------------------------------------------------
#
# Red writes a report and counts attempts; three of the SAME failure escalates
# and stops suggesting; green clears the state and names the next workflow
# stage. A hook cannot invoke a skill, so this is a signal -- and it must never
# block, because the hook that blocked until a skill ran deadlocked and was
# deleted on 2026-08-02.

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d3:
    tmp3 = Path(d3)
    mod.REPO_ROOT = tmp3

    # The bug this catches is worse than the crash that revealed it: the state
    # paths were absolute, baked from REPO_ROOT at import. With REPO_ROOT
    # overridden to a temp dir they still pointed at the real repository, so a
    # test run wrote its failure report into the developer's own tree.
    # Snapshot rather than assert absence. The diagnose loop legitimately
    # writes this file into the real repo whenever the checks go red, so
    # `not exists()` conflated "this call did not write here" with "no session
    # has ever failed a check" -- and the suite went red for an unrelated reason
    # the first time someone fired the hook on a red tree.
    real_report = ROOT / ".claude/hooks/state/check-failure-report.md"
    before = real_report.read_bytes() if real_report.exists() else None

    mod._record_failure("test_x.py: 3 failed", ["a.py"])
    check("the report is written under the CURRENT REPO_ROOT",
          (tmp3 / ".claude/hooks/state/check-failure-report.md").is_file())
    after = real_report.read_bytes() if real_report.exists() else None
    check("...and not into the real repo", before == after)

    body = (tmp3 / ".claude/hooks/state/check-failure-report.md").read_text(
        encoding="utf-8")
    check("the report quotes the failing output", "test_x.py" in body)
    check("the report says to root-cause before changing anything",
          "Root-cause the failure" in body)
    check("the report says it is scratch, not a knowledge doc",
          "not a" in body and "knowledge doc" in body)

    # Digits are normalised: 3 failed -> 2 failed is the same failure getting
    # closer, and must not reset the budget.
    check("the same failure with a different count still counts up",
          mod._record_failure("test_x.py: 2 failed", ["a.py"]) == 2)
    check("...and again", mod._record_failure("test_x.py: 1 failed", ["a.py"]) == 3)
    check("a genuinely different failure resets the budget",
          mod._record_failure("ruff: E501 line too long", ["a.py"]) == 1)

    mod._clear_failures()
    check("clearing removes the state", mod._load_failures() == {})
    check("...and the report file",
          not (tmp3 / ".claude/hooks/state/check-failure-report.md").exists())

    check("MAX_ATTEMPTS is a real ceiling",
          isinstance(mod.MAX_ATTEMPTS, int) and 1 < mod.MAX_ATTEMPTS <= 10)

# Escalation wording, asserted on the source so a rewrite cannot quietly drop it.
_src = HOOK.read_text(encoding="utf-8")
check("escalation stops suggesting rather than looping",
      "Not suggesting another pass" in _src)

# The inverse of the old assertion. This hook ACTS; it must not name a skill in
# anything it prints. Skill names in hook source are an unvalidated copy of a
# routing decision -- three hooks carried them until 2026-08-04, and pointing one
# at a fabricated skill passed every suite. Comments may still explain history;
# only emitted strings are asserted.
import ast as _ast  # noqa: E402, PLC0415

_doc = _ast.get_docstring(_ast.parse(_src)) or ""
_emitted = [n.value for n in _ast.walk(_ast.parse(_src))
            if isinstance(n, _ast.Constant) and isinstance(n.value, str)
            and n.value != _doc and len(n.value) < 4000]
_named = sorted({s for s in ("systematic-debugging", "verifying-work", "code-review",
                             "delivering", "no-slop", "knowledge-manager")
                 if any(s in e for e in _emitted)})
check("the hook names no skill in anything it emits", not _named, f"names {_named}")
check("the loop never blocks the turn",
      '"decision"' not in _src and "block" not in _src.lower().split("deadlock")[0][-2000:])

# --- Task 7: minimal-diff gate ----------------------------------------------
#
# The target says commits must be minimal-diff, mandatorily: every changed
# path must be one TASK.md or the active plan names, or the commit is refused
# with the unnamed paths printed -- a warning would be the one clause among
# seven refusals that nobody reads.
#
# `_hooklib.declared_paths/minimal_diff_violations/minimal_diff_refusal` are
# tested directly against `_hooklib` (already imported and registered in
# `sys.modules` by `load()` above, since the hook module does
# `from _hooklib import ...`) rather than through `mod.main()`. The pure
# functions are worth testing directly whatever the hook does with them; the
# wiring itself is asserted separately, further down, against the hook's source.

_hooklib = sys.modules["_hooklib"]

check("minimal_diff_violations is exposed",
      hasattr(_hooklib, "minimal_diff_violations"))
check("minimal_diff_refusal is exposed",
      hasattr(_hooklib, "minimal_diff_refusal"))
check("declared_paths is exposed", hasattr(_hooklib, "declared_paths"))

check("a declared path is covered",
      _hooklib.minimal_diff_violations(["tools/scope.py"], {"tools/scope.py"}) == [])
# A bare DIRECTORY covers nothing. This assertion is inverted from what it
# said when written, and the inversion is the fix: `tools/` covering
# `tools/x.py` made a prose mention of a directory into a blanket declaration,
# and twelve such tokens in this repo's plans turned the gate off completely.
check("a bare directory does NOT cover the files under it",
      _hooklib.minimal_diff_violations(["tools/scope.py"], {"tools/"})
      == ["tools/scope.py"])
# Declaring a directory on purpose still works -- as a glob, which somebody has
# to type, rather than as a side effect of mentioning a path in a sentence.
check("a declared glob still covers a directory deliberately",
      _hooklib.minimal_diff_violations(["tools/scope.py"], {"tools/*"}) == [])
check("a path matching a declared glob is covered",
      _hooklib.minimal_diff_violations(
          ["prisma/migrations/001/migration.sql"], {"**/migrations/*"}) == [])
check("an undeclared path is a violation",
      _hooklib.minimal_diff_violations(["src/unrelated.py"], {"tools/*"})
      == ["src/unrelated.py"])
check("only the undeclared paths are returned, declared order-preserved",
      _hooklib.minimal_diff_violations(
          ["tools/a.py", "src/b.py", "tools/c.py"], {"tools/*"}) == ["src/b.py"])

# --- against the REAL harvested set, not a fixture ------------------------
#
# The one that would have caught it. Every assertion above drives a synthetic
# `declared` set, and the defect lived in what `declared_paths()` actually
# returns from this repository's own TASK.md and plans -- so all of them passed
# while the running gate committed an undeclared file with no refusal.
#
# Anything asserted about the gate must therefore also be asserted against the
# real input at least once.
_real = _hooklib.declared_paths(root=ROOT)
check("declared_paths harvests no bare directory token",
      not [t for t in _real if t.endswith("/")],
      str(sorted(t for t in _real if t.endswith("/"))[:8]))

# --- the gate reads THIS unit's plan, never every plan ever written --------
#
# It read `docs/plans/*.md` wholesale until 2026-08-10, so a path any closed
# unit had named stayed declared forever and every merged plan permanently
# widened what may be committed unreviewed. The refusal text said "the active
# plan" throughout, which is the defect class this repo names most: prose
# asserting a scoping the wiring does not implement.
_active = _hooklib.active_plans(ROOT)
_all_plans = sorted(p for p in (ROOT / "docs" / "plans").glob("*.md")
                    if p.name.lower() != "readme.md")
check("active_plans selects a subset, not every plan",
      len(_active) < len(_all_plans) or len(_all_plans) <= 1,
      f"{len(_active)} of {len(_all_plans)} -- reading all of them is the defect")
check("...and the refusal message's 'active plan' is now true",
      "active plan" in (_hooklib.minimal_diff_refusal(["zz/undeclared.py"], _real) or ""))
# Selection follows `tools/resume.py`: a `**Slug:**` declaration, then the
# filename. Asserted as a pattern match rather than by importing resume, which
# `_hooklib` must not depend on.
check("the slug pattern matches what writing-plans emits",
      bool(_hooklib.PLAN_SLUG.search("**Slug:** target-workflow\n")))
check("a file no plan names is a violation against the REAL declared set",
      _hooklib.minimal_diff_violations(
          ["tools/_no_plan_names_this.py"], _real) == ["tools/_no_plan_names_this.py"],
      f"{len(_real)} declared tokens covered a file nothing declares")
check("...and the refusal names it",
      "tools/_no_plan_names_this.py" in
      (_hooklib.minimal_diff_refusal(["tools/_no_plan_names_this.py"], _real) or ""))

# A file the active plan DOES name must still be committable, or the gate
# refuses every turn and gets switched off.
#
# Only checkable where a plan exists. An installed layer ships no `docs/plans/`,
# so `_real` there is the knowledge-doc floor and every source file is correctly
# a violation -- which is why the running hook also requires a non-empty
# declaration before applying the gate at all. Reporting that as a failure would
# be asserting this repository's contents in somebody else's.
_declared_beyond_floor = sorted(_real - set(_hooklib.KNOWLEDGE_DOCS))
if not _declared_beyond_floor:
    print("SKIP: no plan declares any path here -- the positive half of the "
          "minimal-diff gate is unmeasured in this repository (the hook's own "
          "guard is asserted separately, against the hook source)")
else:
    _sample = _declared_beyond_floor[0]
    check("a file the plan names is still covered by the REAL declared set",
          _hooklib.minimal_diff_violations([_sample], _real) == [],
          f"the gate must not refuse the very files the plan declares: {_sample}")

# The guard that makes the above safe: no declaration, no gate.
_hooksrc = HOOK.read_text(encoding="utf-8")
check("the hook applies the gate only when something is actually declared",
      "KNOWLEDGE_DOCS" in _hooksrc and "_declared -" in _hooksrc,
      "a source with zero declarations would otherwise refuse every turn")

check("a clean diff refuses nothing",
      _hooklib.minimal_diff_refusal(["tools/scope.py"], {"tools/*"}) is None)
_mdmsg = _hooklib.minimal_diff_refusal(["src/unrelated.py"], {"tools/*"})
check("an unrelated file is refused, not warned",
      isinstance(_mdmsg, str) and "REFUSED" in _mdmsg, str(_mdmsg))
check("the refusal prints the unnamed path",
      isinstance(_mdmsg, str) and "src/unrelated.py" in _mdmsg, str(_mdmsg))
check("many unnamed paths are truncated but the count is stated",
      "6 path(s)" in (_hooklib.minimal_diff_refusal(
          [f"x/{i}.py" for i in range(6)], set()) or ""))

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d4:
    tmp4 = Path(d4)
    # A real repo on a real branch. `declared_paths` now reads only the plan(s)
    # belonging to THIS unit, resolved from the branch the way `tools/resume.py`
    # resolves it -- so a fixture with no branch reads no plan at all, which is
    # correct behaviour and useless as a fixture. Every plan below declares
    # `**Slug:** work` to match.
    new_repo(tmp4)
    write(tmp4, "TASK.md",
          "Prose naming `tools/prose_only.py` declares nothing.\n"
          "- Modify: `tools/scope.py` — this one is a declaration\n")
    (tmp4 / "docs" / "plans").mkdir(parents=True)
    write(tmp4, "docs/plans/2026-08-10-x.md",
          "**Slug:** work\n\n- Modify: `.claude/hooks/_hooklib.py`\n")
    _declared = _hooklib.declared_paths(root=tmp4)
    check("declared_paths reads a declaration line in TASK.md",
          "tools/scope.py" in _declared)
    # The fix, asserted from the other side: a path merely MENTIONED in prose is
    # not declared. Harvesting every backtick is what made the gate inert.
    check("...and ignores a path merely mentioned in prose",
          "tools/prose_only.py" not in _declared, str(sorted(_declared)))
    check("declared_paths reads docs/plans/*.md",
          ".claude/hooks/_hooklib.py" in _declared)
    # A root-level file is declarable. Requiring a `/` in the token was right
    # for prose scanning and wrong on a declaration line: it silently made
    # `CLAUDE.md`, `README.md` and `.gitignore` undeclarable, so the gate
    # refused three files the plan explicitly named. Found by firing the hook.
    write(tmp4, "docs/plans/2026-08-10-z.md",
          "**Slug:** work\n\n- Modify: `CLAUDE.md` — policy\n"
          "- Modify: `.gitignore` — ignore it\n")
    _declared2 = _hooklib.declared_paths(root=tmp4)
    check("a root-level file can be declared", "CLAUDE.md" in _declared2,
          str(sorted(_declared2)))
    check("...including a dotfile with no extension",
          ".gitignore" in _declared2, str(sorted(_declared2)))
    check("...while a bare directory still is not",
          _hooklib.minimal_diff_violations(["docs/x.md"], _declared2)
          == ["docs/x.md"])

    # The File map TABLE is a declaration. `writing-plans` C2 calls it the
    # frozen file map, and it is not always a subset of the per-task bullets:
    # `.gitignore` was declared only there and was refused on that basis, while
    # `README.md` looked covered purely because an unrelated older plan named
    # it -- coverage right by accident, which is the hardest kind to notice
    # going wrong.
    write(tmp4, "docs/plans/2026-08-10-tbl.md",
          "**Slug:** work\n\n"
          "| File | Action | Responsibility |\n"
          "|---|---|---|\n"
          "| `src/only_in_table.py` | Create | nothing else names it |\n"
          "| `a.md`, `b.md` | Modify | two in one row |\n")
    _tbl = _hooklib.declared_paths(root=tmp4)
    check("a File map table row declares its file",
          "src/only_in_table.py" in _tbl, str(sorted(_tbl)))
    check("...including every file in a multi-file row",
          {"a.md", "b.md"} <= _tbl, str(sorted(_tbl)))
    check("...while the Responsibility column is not harvested",
          not [t for t in _tbl if " " in t], str(sorted(_tbl)))
    check("declared_paths always covers the knowledge docs",
          {"LOG.md", "HANDOFF.md", "TASK.md"} <= _declared)
    check("declared_paths is silent, not raising, on a root with no plans dir",
          isinstance(_hooklib.declared_paths(root=tmp4 / "nowhere"), set))

# The gate is wired, and this assertion is the whole reason to keep it.
#
# It was written inverted -- "the running hook does NOT yet call the gate" --
# by the agent that built the gate but was not permitted to wire it, its
# declared files not including the hook. That is the correct behaviour and it
# is why the inverted form existed: a gap asserted cannot be forgotten, where a
# gap merely mentioned in a report can.
#
# The dispatcher then declared the file and wired it, so the assertion flips
# rather than being deleted. A tested function nothing calls is prose with a
# test suite attached, and that is the failure mode this repository names most
# often: a document asserting what the wiring does not do.
hook_src = HOOK.read_text(encoding="utf-8")
check("the running hook calls the minimal-diff gate",
      "minimal_diff_refusal(" in hook_src)
check("...and speaks its refusal rather than committing anyway",
      "speak(unrelated)" in hook_src)
check("...and imports it from _hooklib rather than restating the rule",
      "minimal_diff_refusal," in hook_src and "declared_paths," in hook_src)

# The gate must not apply where nothing could declare a path. Ten end-to-end
# cases below commit in a temp repo with no plan in it, and every one refused
# when the gate was first wired -- this layer installs into repositories that
# have never written a plan, and a gate that stops every checkpoint there is
# not strict, it is broken.
check("the hook checks a declaration source exists before applying the gate",
      "declaration_sources(REPO_ROOT)" in hook_src)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as _dn:
    _bare = Path(_dn)
    check("a repo with no TASK.md and no plans has no declaration source",
          _hooklib.declaration_sources(root=_bare) == [],
          str(_hooklib.declaration_sources(root=_bare)))
    write(_bare, "TASK.md", "Goal: something\n")
    check("...and a TASK.md alone is a source",
          _hooklib.declaration_sources(root=_bare) == ["TASK.md"],
          str(_hooklib.declaration_sources(root=_bare)))
    (_bare / "docs" / "plans").mkdir(parents=True)
    write(_bare, "docs/plans/2026-08-10-y.md", "- Modify: `tools/x.py`\n")
    check("...as is a plan, and both are listed",
          _hooklib.declaration_sources(root=_bare) ==
          ["TASK.md", "docs/plans/2026-08-10-y.md"],
          str(_hooklib.declaration_sources(root=_bare)))

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All artifact-autocommit tests passed")

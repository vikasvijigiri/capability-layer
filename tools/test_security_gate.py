#!/usr/bin/env python3
"""Every clause is independently provable, and inverting one alone flips the exit.

Why this suite exists
---------------------
The gate's value is entirely in whether each clause actually fires. A clause that
cannot be shown to go red on its own case is decoration, and decoration in a
security check is worse than nothing because it reads as coverage.

The shape is `test_scope.py`'s, deliberately: a facts dict that fires nothing,
then the same dict with one clause's fact inverted. If the second does not exit
`1`, that clause does not work.

`evaluate` is pure and `gather_facts(offline=True)` returns None for every fact,
so nothing here touches git, the network or the clock.

No literal credential appears in this file. Every secret fixture is assembled
from parts at runtime -- a realistic one in a test made this repository
uncommittable the last time somebody wrote one down, which `_hooklib`'s own
comment records.

Run: python tools/test_security_gate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import security_gate as sg  # noqa: E402

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


# A branch that fires nothing: nothing removed, nothing secret, one mapped
# non-sensitive path, one read-only agent, no dependency change.
QUIET: dict = {
    "removed_table_entries": {},
    "added_lines": ["def hello():", "    return 1"],
    "secret_patterns": sg._secret_patterns(),
    "changed_paths": ["tools/a.py"],
    "sensitive_patterns": ["**/auth/**", "pyproject.toml"],
    "test_map": {"tools/*.py": "python tools/test_a.py"},
    "agents": [{"path": ".claude/agents/reader.md", "can_write": False,
                "allowed_paths": False}],
    "deps_exit": 0,
    "dependency_considered": False,
    "allows": set(),
}

check("the secret patterns actually loaded", bool(QUIET["secret_patterns"]),
      "importing _hooklib.SECRET_PATTERNS returned nothing")

quiet = sg.evaluate(QUIET)
check("a quiet branch produces no finding", quiet == [], str(quiet))
check("...and exits 0", sg.exit_code(quiet) == 0)
check("...over four clauses, dependency-risk not applicable",
      sg.considered(QUIET) == [c for c in sg.CLAUSES if c != "dependency-risk"],
      str(sg.considered(QUIET)))

# --- one inversion per clause ------------------------------------------------
#
# Assembled rather than written out: `sk-` + 32 chars is a real OpenAI-shaped
# key and this file is scanned by the same patterns it is testing.
FAKE_SECRET = "sk-" + "a1b2c3d4" * 4

INVERSIONS: dict[str, dict] = {
    "control-weakened": {
        "removed_table_entries": {"tools/scope.py:SENSITIVE_PATTERNS": ["'**/auth/**'"]},
    },
    "secret-in-branch": {
        "added_lines": [f'    key = "{FAKE_SECRET}"'],
    },
    "sensitive-unmapped": {
        "changed_paths": ["src/auth/session.py"],
    },
    "agent-unscoped": {
        "agents": [{"path": ".claude/agents/writer.md", "can_write": True,
                    "allowed_paths": False}],
    },
    "dependency-risk": {
        "dependency_considered": True, "deps_exit": 1,
    },
}

for clause, inversion in INVERSIONS.items():
    got = sg.evaluate(dict(QUIET, **inversion))
    fired = [f["clause"] for f in got if f["severity"] == "blocking"]
    check(f"[{clause}] inverting it alone fires it", fired == [clause],
          f"fired {fired}")
    check(f"[{clause}] ...and the run exits 1", sg.exit_code(got) == 1,
          str(sg.exit_code(got)))

# --- the sensitive path must be BOTH sensitive and unmapped ------------------
mapped = sg.evaluate(dict(QUIET, changed_paths=["src/auth/session.py"],
                          test_map={"src/auth/*.py": "python tools/test_auth.py"}))
check("a sensitive path that IS mapped does not fire", mapped == [], str(mapped))

insensitive = sg.evaluate(dict(QUIET, changed_paths=["src/unmapped.py"]))
check("an unmapped path that is not sensitive does not fire here",
      insensitive == [], str(insensitive))

# --- unknown is never a pass -------------------------------------------------
for key in ("removed_table_entries", "added_lines", "changed_paths", "agents"):
    got = sg.evaluate(dict(QUIET, **{key: None}))
    sev = {f["severity"] for f in got}
    check(f"[{key}=None] reports unknown, never a pass", sev == {"unknown"}, str(got))
    check(f"[{key}=None] ...and exits 2, not 0", sg.exit_code(got) == 2)

offline = sg.gather_facts(Path("."), "main", offline=True)
off = sg.evaluate(offline)
check("--offline evaluates nothing and exits 2", sg.exit_code(off) == 2,
      str(sg.exit_code(off)))
check("...with every applicable clause named unknown",
      {f["clause"] for f in off} == {c for c in sg.CLAUSES if c != "dependency-risk"},
      str({f["clause"] for f in off}))

# --- a blocking clause outranks an unknown one -------------------------------
both = sg.evaluate(dict(QUIET, added_lines=None,
                        removed_table_entries={"tools/scope.py:CONTROL_PATTERNS": ["'x'"]}))
check("blocking outranks unknown in the exit code", sg.exit_code(both) == 1,
      str(sg.exit_code(both)))

# --- the allow marker --------------------------------------------------------
allowed = sg.evaluate(dict(QUIET, allows={"control-weakened"},
                           **INVERSIONS["control-weakened"]))
check("an inline allow stops its clause blocking",
      sg.exit_code(allowed) == 0, str(sg.exit_code(allowed)))
# ...but it is REPORTED. A waiver that vanishes from the output makes "did not
# fire" and "fired, waived" the same result, which is the property that made a
# forged receipt indistinguishable from a real one.
check("...and is still reported, as advisory rather than dropped",
      [(f["clause"], f["severity"]) for f in allowed]
      == [("control-weakened", "advisory")], str(allowed))
check("...naming it as waived, so a reader can see the escape hatch was used",
      bool(allowed) and allowed[0]["finding"].startswith("WAIVED"), str(allowed))

other = sg.evaluate(dict(QUIET, allows={"secret-in-branch"},
                         **INVERSIONS["control-weakened"]))
check("...and suppresses no other clause",
      [(f["clause"], f["severity"]) for f in other]
      == [("control-weakened", "blocking")], str(other))
check("...so an allow for the wrong clause still exits 1",
      sg.exit_code(other) == 1, str(sg.exit_code(other)))

unknown_allowed = sg.evaluate(dict(QUIET, allows={"secret-in-branch"}, added_lines=None))
check("an allow cannot suppress an unknown -- only a person can supply the fact",
      sg.exit_code(unknown_allowed) == 2, str(unknown_allowed))

check("an allow with no reason does not parse",
      sg.ALLOW_RE.search("# security-gate: allow control-weakened --") is None)
check("...and one with a reason does",
      (sg.ALLOW_RE.search("# security-gate: allow control-weakened -- the pattern moved")
       or [None])[0] is not None)

# --- review round 1: what an allow may NOT waive -----------------------------
#
# The first version waived any clause, so a credential plus one comment line
# exited 0. Each unwaivable clause gets its own case: a waiver list is exactly
# the kind of table that grows by accident.
for _clause in sg.CLAUSES:
    _facts = dict(QUIET, allows={_clause}, **INVERSIONS[_clause])
    _got = sg.evaluate(_facts)
    if _clause in sg.WAIVABLE_CLAUSES:
        check(f"[{_clause}] is waivable, and the waiver is reported",
              sg.exit_code(_got) == 0
              and [f["severity"] for f in _got] == ["advisory"], str(_got))
    else:
        check(f"[{_clause}] CANNOT be waived by an inline allow",
              sg.exit_code(_got) == 1, str(_got))
        check(f"[{_clause}] ...and the useless allow is named, not ignored",
              any("does NOT apply" in f["finding"] for f in _got), str(_got))

check("a credential specifically cannot be waived",
      "secret-in-branch" not in sg.WAIVABLE_CLAUSES)

# --- review round 1: a deleted check kind is a removal, not just `false` ------
_was = '{"audit": ["pip-audit"], "lint": ["ruff"], "_why_audit": "note"}'
_now_false = '{"audit": false, "lint": ["ruff"]}'
_now_gone = '{"lint": ["ruff"]}'
check("a kind set to false is disabled",
      sg.disabled_check_kinds(_now_false) == {"audit"})
_was_on, _gone_on = (sg.configured_check_kinds(_was) or set(),
                     sg.configured_check_kinds(_now_gone) or set())
check("a kind DELETED outright is no longer configured",
      _was_on - _gone_on == {"audit"}, str(_gone_on))
check("...while deleting a `_why_` note is not a finding",
      sg.configured_check_kinds(_was) == sg.configured_check_kinds(
          '{"audit": ["pip-audit"], "lint": ["ruff"]}'))
check("configured_check_kinds returns None for unreadable JSON",
      sg.configured_check_kinds("{not json") is None)

# --- table_entries: the parser the control-weakened clause rests on ----------
SRC = "\n".join([
    "import re",
    "PATTERNS = [re.compile(r'a'), re.compile(r'b')]",
    "TIERS = {'x': 'high', 'y': 'low'}",
    "NOT_A_TABLE = 3",
])
# `ast.unparse` normalises as it goes -- `r'a'` comes back as `'a'`. That is the
# behaviour we want and it is asserted rather than tolerated: re-quoting or
# reformatting a pattern must NOT read as removing it, or the clause goes red on
# every `ruff format` and gets switched off within a week.
check("table_entries reads a list of calls, not just literals",
      sg.table_entries(SRC, "PATTERNS") == ["re.compile('a')", "re.compile('b')"],
      str(sg.table_entries(SRC, "PATTERNS")))
check("...normalising quote style, so reformatting is not a removal",
      sg.table_entries("X = [r'a']", "X") == sg.table_entries('X = ["a"]', "X"))
check("...and a dict, as key: value pairs",
      sg.table_entries(SRC, "TIERS") == ["'x': 'high'", "'y': 'low'"],
      str(sg.table_entries(SRC, "TIERS")))
check("...and returns None for a name that is not a table",
      sg.table_entries(SRC, "NOT_A_TABLE") is None)
check("...and None for an absent name", sg.table_entries(SRC, "NOPE") is None)
check("...and None for a file that does not parse",
      sg.table_entries("def (:", "PATTERNS") is None)

check("disabled_check_kinds finds a kind switched off",
      sg.disabled_check_kinds('{"audit": false, "lint": "ruff"}') == {"audit"})
check("...and returns None for unreadable JSON",
      sg.disabled_check_kinds("{not json") is None)

# --- every watched table still exists, or the clause guards nothing ----------
for rel, names in sg.WATCHED_TABLES.items():
    src = (sg.ROOT / rel).read_text(encoding="utf-8", errors="ignore")
    for name in names:
        check(f"watched table {rel}:{name} still exists",
              sg.table_entries(src, name) is not None,
              "renamed or removed -- the clause silently guards nothing")

# --- the base ref must resolve on a CI pull-request checkout ------------------
#
# `--base main` names a LOCAL branch. On a PR checkout `actions/checkout` checks
# out the merge commit and leaves the base reachable only as `origin/main`, so
# `merge-base main HEAD` fails, every fact comes back `None`, and all five
# clauses degrade to `unknown` -- exit 2. Correct fail-closed behaviour and a
# useless diagnosis: on PR #12 this was green locally and red on CI, and the one
# line the runner surfaced named a different clause entirely.
#
# Proven against a real clone with no local `main` (exit 2 -> exit 0), and
# asserted here on the resolution itself, which is the part that has to hold.

import subprocess  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, stdin=subprocess.DEVNULL)


_tmp = Path(tempfile.mkdtemp())
_origin, _clone = _tmp / "origin", _tmp / "clone"
_origin.mkdir()
_git("init", "--quiet", "--initial-branch=main", cwd=_origin)
_git("config", "user.email", "t@example.com", cwd=_origin)
_git("config", "user.name", "t", cwd=_origin)
(_origin / "a.txt").write_text("one\n", encoding="utf-8")
_git("add", "-A", cwd=_origin)
_git("commit", "--quiet", "-m", "base", cwd=_origin)
_git("clone", "--quiet", str(_origin), str(_clone), cwd=_tmp)
# The CI shape exactly: detach, then delete every local branch, so the base
# exists only as a remote-tracking ref.
_git("checkout", "--quiet", "--detach", "HEAD", cwd=_clone)
_git("branch", "-D", "main", cwd=_clone)

check("the CI shape really has no local base branch",
      _git("rev-parse", "--verify", "--quiet", "main", cwd=_clone).returncode != 0,
      "the fixture must reproduce the failure before it can prove the fix")
check("resolve_base falls back to the remote-tracking ref",
      sg.resolve_base("main", _clone) == "origin/main",
      str(sg.resolve_base("main", _clone)))
check("...and merge-base answers against what it returned",
      bool(sg._git(["merge-base", sg.resolve_base("main", _clone) or "main",
                    "HEAD"], _clone)),
      "this is the call that returned nothing and unknown'd every clause")

# A local branch WINS over a remote-tracking one of the same name: a caller who
# says `--base main` in a repo that has one means that one, and silently
# preferring `origin/main` would compare against whatever was last fetched.
check("an explicit local ref is preferred over origin/",
      sg.resolve_base("main", sg.ROOT) == "main",
      str(sg.resolve_base("main", sg.ROOT)))
check("a ref that resolves in neither form is None, not a guess",
      sg.resolve_base("no-such-ref-anywhere", _clone) is None,
      "inventing an origin/ variant would report a base nobody named")

print()
if failures:
    print(f"FAIL: {len(failures)} check(s) failed")
    raise SystemExit(1)
print("OK: security_gate -- every clause proven by inverting it alone")

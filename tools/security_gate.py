#!/usr/bin/env python3
"""Does this branch weaken a security control, or leave one unchecked?

    python tools/security_gate.py --base main
    python tools/security_gate.py --base main --json
    python tools/security_gate.py --offline        # every fact None; exits 2

Exit `0` clean, `1` a clause fired, `2` a clause could not be evaluated. `2` is
deliberately not `0` -- folding "I could not tell" into "fine" is the silent
degradation Article V forbids, and `delivery_check.exit_code` makes the same
call for the same reason.

Why this is not a receipt
-------------------------
The obvious shape for a security gate is a record that a review happened. This
repository built that and deleted it. `permission-security/03-review-gate.py` wrote into
`.claude/hooks/state/review-receipts.json`, and it failed twice over:

- the receipts file was tracked, so `--record` changed the very fingerprint it
  had just recorded under, and every receipt self-invalidated the instant it was
  written -- the gate had never once been able to pass;
- *"a forged receipt and a real one are the same file"*. The model ran
  `--record` and wrote a receipt asserting a sign-off that had not happened, one
  turn after authoring the rule forbidding exactly that.

It went out on 2026-08-02 with every other process-compliance gate, under the
finding *"Every hook verifies an artefact. Not one enforces process."*

So every clause here is a fact about the artefact, computable from two git
revisions by anyone at any time, with no state to keep and none to forge. A
clause that needed someone to have done something would be the receipt again in
a different costume.

The escape hatch has the same property
--------------------------------------
`# security-gate: allow <clause> -- <reason>` on any changed line, following
ruff's `# noqa` and mypy's `# type: ignore`. It suppresses that clause for this
run. It lives in the diff a reviewer reads and can be recorded nowhere else --
which is the whole difference between it and a receipt. A reason is required:
an allow with no reason is boilerplate, and boilerplate reads as considered when
it was not.

Tables are imported, never copied
---------------------------------
`_hooklib.SECRET_PATTERNS`, `scope.SENSITIVE_PATTERNS` and the rest are loaded
from their own modules. A second copy would drift, and the copy that drifted
would be the one guarding the unattended path -- `scope._migration_patterns()`
already exists for this reason and this file follows it.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLAUSES = ("control-weakened", "secret-in-branch", "sensitive-unmapped",
           "agent-unscoped", "dependency-risk")

# Which module-level names are security controls. A change that shortens one of
# these is the change this gate exists for: every other clause here notices a
# bad thing arriving, and only this one notices a guard leaving.
WATCHED_TABLES = {
    ".claude/hooks/_hooklib.py": ("SECRET_PATTERNS", "SECRET_PATH_PATTERNS",
                                  "AI_ATTRIBUTION_PATTERNS",
                                  "MIGRATION_PATH_PATTERNS"),
    "tools/scope.py": ("SENSITIVE_PATTERNS", "CONTROL_PATTERNS", "CLAUSE_TIER"),
}

# Not a module, so it gets its own comparison: a check kind set to `false` is a
# gate switched off, which is the JSON spelling of removing a table entry.
PROJECT_CHECKS = ".claude/project-checks.json"

# The kinds `_projectchecks.py` resolves. Used to tell "this gate was removed"
# from "a comment was removed".
CHECK_KINDS = ("lint", "typecheck", "test", "build", "audit", "e2e", "smoke")

# Files whose changing means the dependency tree moved, so `deps.py` has
# something new to say. Absent from a diff, the clause is not applicable rather
# than passing -- see `considered` in the result.
DEPENDENCY_FILES = ("pyproject.toml", "requirements.txt", "requirements/*.txt",
                    "poetry.lock", "uv.lock", "package.json", "package-lock.json",
                    "yarn.lock", "pnpm-lock.yaml", "Cargo.toml", "Cargo.lock",
                    "go.mod", "go.sum", "Gemfile.lock")

# The tools that let an agent write. An agent holding one of these and declaring
# no `allowed-paths:` is denied by `pre-edit/02-agent-scope-guard.py` -- but only
# on a host that sets `UAIOS_AGENT_NAME`, and Claude Code does not, so on this
# host the guard is silent and this clause is the only thing checking the pair.
# See the dormancy note in `.claude/workflow.md`. That makes this a static check
# with no runtime backstop here, which is a reason to keep it, not to drop it.
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")

# `--` and the em dash both, because this file is edited by hand and by tools
# that normalise one into the other. The reason group is required: `.+` and not
# `.*`.
ALLOW_RE = re.compile(r"#\s*security-gate:\s*allow\s+([a-z][a-z-]+)\s*(?:—|--)\s*(\S.*)")

# Which clauses an inline allow may waive, and it is not all of them.
#
# The first version waived any clause, and review round 1 found what that means:
# a credential in the diff plus one comment line beside it exited 0. That is the
# receipt's actual failure mode -- a self-certified pass -- wearing the escape
# hatch's clothes, and it contradicted `code-review`'s own rule that a
# high-severity security finding is never auto-waived.
#
# The distinction is whether a legitimate reason can exist. A pattern genuinely
# moves between tables, and a sensitive path can genuinely be covered by
# something the map cannot express -- those are design decisions, and a decision
# with its reason in the diff is exactly what should be waivable. There is no
# reason that makes a committed credential, an unscoped write capability, or a
# denied licence acceptable; each of those has a real fix that is not a comment.
WAIVABLE_CLAUSES = ("control-weakened", "sensitive-unmapped")


# --- loading the tables we do not own ----------------------------------------

def _load(rel: str, name: str):
    """Import a module by path. Mirrors `scope._load`, including its silence."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _secret_patterns() -> list | None:
    mod = _load(".claude/hooks/_hooklib.py", "hooklib_security_gate")
    pats = getattr(mod, "SECRET_PATTERNS", None) if mod else None
    return list(pats) if pats else None


def _scope_module():
    return _load("tools/scope.py", "scope_security_gate")


# --- reading a table out of a revision ---------------------------------------

def table_entries(source: str, name: str) -> list[str] | None:
    """The entries of a module-level list or dict, as source text. None if absent.

    Source text and not `ast.literal_eval`, which was the plan's word for this
    and does not survive contact: `SECRET_PATTERNS` is a list of `re.compile(...)`
    CALLS, so there is no literal to evaluate. Unparsing each element compares
    the same unit a reader would call "an entry" and works for both a list of
    strings and a list of expressions.

    None rather than `[]` when the table cannot be found or the file cannot be
    parsed. An unreadable table reporting "nothing was removed" is the exact
    silent pass this file exists to refuse.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        targets: list = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in targets):
            continue
        value = node.value
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return [ast.unparse(e) for e in value.elts]
        if isinstance(value, ast.Dict):
            # A `**spread` entry has a key of None. Unparsing the value alone
            # keeps the entry comparable instead of crashing on it.
            return [f"{ast.unparse(k)}: {ast.unparse(v)}" if k is not None
                    else f"**{ast.unparse(v)}"
                    for k, v in zip(value.keys, value.values, strict=True)]
        return None
    return None


def disabled_check_kinds(text: str) -> set[str] | None:
    """The keys of `project-checks.json` whose value is exactly `false`."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return {k for k, v in data.items() if v is False}


def configured_check_kinds(text: str) -> set[str] | None:
    """The known check kinds this config configures, `false` excluded.

    Paired with `disabled_check_kinds` because there are two ways to switch a
    gate off and only one of them writes the word `false`. Deleting
    `"audit": [...]` outright falls back to auto-detection, which may resolve to
    nothing at all -- so a kind that WAS configured and now is not is a removal,
    and review round 1 found the first version blind to it.

    Only `CHECK_KINDS` counts, so deleting a `_why_` note is not a finding.
    """
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return {k for k in CHECK_KINDS if k in data and data[k] is not False}


# --- the decision, pure ------------------------------------------------------

def evaluate(facts: dict) -> list[dict]:
    """Findings for one branch. Pure: the whole input is the dict.

    Every clause resolves to exactly one of `blocking`, `advisory` or `unknown`,
    and a fact of None is `unknown` -- never absent, never a pass. A clause that
    does not apply to this diff is reported through `considered`, not as a pass.
    """
    out: list[dict] = []
    allows = set(facts.get("allows") or ())

    def add(clause: str, severity: str, finding: str, detail=None) -> None:
        # A waived clause is REPORTED as advisory, never dropped. Dropping it
        # was the first version and it quietly undid the design: the whole
        # argument for an inline allow over a receipt is that the waiver is
        # visible, and a silent `return` here makes "did not fire" and "fired,
        # waived" the same output -- which is the property that made a forged
        # receipt indistinguishable from a real one.
        if clause in allows and severity == "blocking":
            if clause not in WAIVABLE_CLAUSES:
                # Reported, not ignored. An allow that does nothing must say so,
                # or the author believes they have handled it.
                out.append({"clause": clause, "severity": "blocking",
                            "finding": f"{finding} An inline allow was present "
                                       f"and does NOT apply: `{clause}` is not "
                                       f"waivable, because no reason makes this "
                                       f"acceptable.",
                            "detail": list(detail or [])})
                return
            out.append({"clause": clause, "severity": "advisory",
                        "finding": f"WAIVED by an inline allow: {finding}",
                        "detail": list(detail or [])})
            return
        out.append({"clause": clause, "severity": severity,
                    "finding": finding, "detail": list(detail or [])})

    def unknown(clause: str, what: str) -> None:
        out.append({"clause": clause, "severity": "unknown",
                    "finding": f"could not determine {what} -- unrun, not passed",
                    "detail": []})

    # --- control-weakened: the only clause that notices a guard LEAVING
    removed = facts.get("removed_table_entries")
    if removed is None:
        unknown("control-weakened", "what the watched security tables held at the base")
    else:
        gone = {k: v for k, v in removed.items() if v}
        if gone:
            detail = [f"{k} lost {len(v)}: {', '.join(sorted(v)[:3])}"
                      + ("…" if len(v) > 3 else "") for k, v in sorted(gone.items())]
            add("control-weakened", "blocking",
                f"{len(gone)} security control(s) hold fewer entries than at the "
                f"base. Removing a guard is not a refactor; declare it with an "
                f"inline `# security-gate: allow control-weakened -- <reason>`.",
                detail)

    # --- secret-in-branch: the whole branch, not one commit
    added = facts.get("added_lines")
    patterns = facts.get("secret_patterns")
    if added is None or patterns is None:
        unknown("secret-in-branch", "the lines this branch adds")
    else:
        hits = []
        for line in added:
            for pat in patterns:
                if pat.search(line):
                    hits.append(pat.pattern[:48])
                    break
        if hits:
            # The matching LINE is never printed. Printing it would put the
            # credential into a check's output, which is logged in CI.
            add("secret-in-branch", "blocking",
                f"{len(hits)} added line(s) match a secret pattern. "
                f"`permission-security/01-secret-scan.py` sees one commit at a time, so a "
                f"secret added mid-branch and still present at HEAD is never "
                f"looked at again.",
                sorted({f"pattern {h}" for h in hits}))

    # --- sensitive-unmapped: `scope.py` deliberately will not do this
    paths = facts.get("changed_paths")
    sensitive_patterns = facts.get("sensitive_patterns")
    test_map = facts.get("test_map")
    if paths is None or sensitive_patterns is None or test_map is None:
        unknown("sensitive-unmapped", "which changed paths are sensitive and mapped")
    else:
        sensitive = [p for p in paths
                     if any(fnmatch.fnmatch(p, pat) for pat in sensitive_patterns)]
        unmapped = [p for p in sensitive
                    if not any(fnmatch.fnmatch(p, g) for g in test_map)]
        if unmapped:
            add("sensitive-unmapped", "blocking",
                f"{len(unmapped)} sensitive path(s) are covered by no suite in "
                f"`test_map`. `scope.CLAUSE_TIER` omits `unmapped` on the grounds "
                f"that it is a gap in the map rather than a fact about danger -- "
                f"true in general, false on these paths.",
                unmapped)

    # --- agent-unscoped: a write capability with no declared scope
    agents = facts.get("agents")
    if agents is None:
        unknown("agent-unscoped", "which changed agents may write")
    else:
        bad = [a["path"] for a in agents
               if a.get("can_write") and not a.get("allowed_paths")]
        if bad:
            add("agent-unscoped", "blocking",
                f"{len(bad)} changed agent(s) may write and declare no "
                f"`allowed-paths:`. `pre-edit/02-agent-scope-guard.py` denies an "
                f"unscoped write, so the defect presents as a silent agent "
                f"failure mid-dispatch rather than as an error here.",
                bad)

    # --- dependency-risk: only when the tree actually moved
    if facts.get("dependency_considered"):
        code = facts.get("deps_exit")
        if code is None:
            unknown("dependency-risk", "the licence verdict for the changed tree")
        elif code == 2:
            unknown("dependency-risk", "a licence `tools/deps.py` could not read")
        elif code != 0:
            add("dependency-risk", "blocking",
                f"this branch changes a dependency declaration and "
                f"`python tools/deps.py` exits {code}.", [])

    return out


def considered(facts: dict) -> list[str]:
    """The clauses this run had anything to say about."""
    if facts.get("dependency_considered"):
        return list(CLAUSES)
    return [c for c in CLAUSES if c != "dependency-risk"]


def exit_code(findings: list[dict]) -> int:
    """0 clean · 1 a clause fired · 2 a clause could not be evaluated."""
    severities = {f["severity"] for f in findings}
    if "blocking" in severities:
        return 1
    if "unknown" in severities:
        return 2
    return 0


# --- the seam: every subprocess in the file lives below this line -------------

def _git(args: list[str], root: Path) -> str | None:
    """`encoding` is not optional here, and getting it wrong is a false positive.

    `text=True` alone decodes with the console's preferred encoding -- cp1252 on
    Windows. Measured on the first real run: the emoji in
    `_hooklib.AI_ATTRIBUTION_PATTERNS` came back from `git show` mojibaked while
    the head side was read as UTF-8, the two entries compared unequal, and
    `control-weakened` reported a guard removed that nobody had touched. A
    security gate that cries wolf on a locale difference gets switched off.
    """
    try:
        done = subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, timeout=30,
                              stdin=subprocess.DEVNULL,
                              encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _agent_facts(root: Path, paths: list[str]) -> list[dict]:
    out = []
    for rel in paths:
        if not fnmatch.fnmatch(rel, ".claude/agents/*.md"):
            continue
        path = root / rel
        if not path.is_file():
            continue                     # deleted; nothing left to be unscoped
        text = path.read_text(encoding="utf-8", errors="ignore")
        head = text.split("---", 2)[1] if text.startswith("---") else ""
        tools_line = ""
        for line in head.splitlines():
            if line.strip().lower().startswith("tools:"):
                tools_line = line.split(":", 1)[1]
        out.append({
            "path": rel,
            "can_write": any(t in tools_line for t in WRITE_TOOLS) or "*" in tools_line,
            "allowed_paths": any(ln.strip().lower().startswith("allowed-paths:")
                                 for ln in head.splitlines()),
        })
    return out


def resolve_base(base: str, root: Path) -> str | None:
    """The given ref if it resolves here, else its `origin/` form, else None.

    `--base main` names a LOCAL branch, and on a CI pull-request checkout there
    is no local `main`: `actions/checkout` checks out the merge commit and
    leaves the base reachable only as `origin/main`. `merge-base main HEAD` then
    fails, every fact this module reads comes back `None`, and all five clauses
    degrade to `unknown` -- exit 2, which is correct fail-closed behaviour and a
    useless diagnosis. Measured on PR #12: green locally, red on CI, and the one
    line the runner reported was `not applicable to this diff: dependency-risk`,
    which describes a different clause entirely.

    Tried in order and never guessed past: an explicit ref the caller named wins
    over a remote-tracking one with the same name, because a caller who says
    `--base main` in a repository that HAS a local `main` means that one.

    `None` means neither form resolved. The caller keeps the original string so
    the failure still reports the ref the user actually asked for, rather than
    an invented `origin/` variant they never mentioned.
    """
    for candidate in (base, f"origin/{base}", f"refs/remotes/origin/{base}"):
        if _git(["rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
                root):
            return candidate
    return None


def gather_facts(root: Path, base: str, offline: bool = False) -> dict:
    """Everything `evaluate` reads. `offline=True` returns None for every fact.

    The offline mode is what makes the suite hermetic: it exercises the same
    `evaluate` the real run does, with no repository, no network and no clock.
    """
    facts: dict = {
        "removed_table_entries": None, "added_lines": None, "secret_patterns": None,
        "changed_paths": None, "sensitive_patterns": None, "test_map": None,
        "agents": None, "deps_exit": None, "dependency_considered": False,
        "allows": set(),
    }
    if offline:
        return facts

    base = resolve_base(base, root) or base
    merge_base = _git(["merge-base", base, "HEAD"], root)
    merge_base = merge_base.strip() if merge_base else None

    names = _git(["diff", "--name-only", f"{base}...HEAD"], root) if merge_base else None
    status = _git(["status", "--porcelain=v1", "-uall"], root)
    paths: set[str] = set()
    if names is not None:
        paths.update(p.strip() for p in names.splitlines() if p.strip())
    if status is not None:
        paths.update(line[3:].strip().replace("\\", "/")
                     for line in status.splitlines() if len(line) > 3)
    if names is not None or status is not None:
        facts["changed_paths"] = sorted(p.replace("\\", "/") for p in paths if p)
        facts["agents"] = _agent_facts(root, facts["changed_paths"])

    # added lines, and the allow markers that live among them
    diff = _git(["diff", "--unified=0", f"{base}...HEAD"], root) if merge_base else None
    worktree = _git(["diff", "--unified=0", "HEAD"], root)
    if diff is not None or worktree is not None:
        added = [ln[1:] for ln in ((diff or "") + "\n" + (worktree or "")).splitlines()
                 if ln.startswith("+") and not ln.startswith("+++")]
        facts["added_lines"] = added
        facts["allows"] = {m.group(1) for ln in added
                           for m in [ALLOW_RE.search(ln)] if m}
    facts["secret_patterns"] = _secret_patterns()

    scope_mod = _scope_module()
    if scope_mod is not None:
        facts["sensitive_patterns"] = list(
            getattr(scope_mod, "SENSITIVE_PATTERNS", []) or []) or None

    checks_path = root / PROJECT_CHECKS
    if checks_path.is_file():
        try:
            data = json.loads(checks_path.read_text(encoding="utf-8"))
            facts["test_map"] = data.get("test_map")
        except (OSError, ValueError):
            pass

    # what the watched tables lost between base and head
    if merge_base is not None:
        removed: dict = {}
        readable = True
        for rel, names_ in WATCHED_TABLES.items():
            old_src = _git(["show", f"{merge_base}:{rel}"], root)
            new_path = root / rel
            new_src = (new_path.read_text(encoding="utf-8", errors="ignore")
                       if new_path.is_file() else None)
            if old_src is None:
                # `_git` returns None for "the path is absent at the base" AND
                # for "git failed", and review round 1 found that reading both
                # as nothing-to-lose makes a transient git failure a PASS on the
                # one clause that notices a guard leaving. `cat-file -e` decides
                # which: it exits 0 iff the object exists.
                if _git(["cat-file", "-e", f"{merge_base}:{rel}"], root) is None:
                    continue             # genuinely absent at the base
                readable = False         # present, but could not be read
                continue
            if new_src is None:
                removed[f"{rel} (deleted)"] = ["the whole file"]
                continue
            for table in names_:
                old = table_entries(old_src, table)
                new = table_entries(new_src, table)
                if old is None:
                    continue             # absent at the base is not a removal
                if new is None:
                    readable = False
                    continue
                lost = [e for e in old if e not in new]
                if lost:
                    removed[f"{rel}:{table}"] = lost
        old_checks = _git(["show", f"{merge_base}:{PROJECT_CHECKS}"], root)
        if old_checks is not None and checks_path.is_file():
            was = disabled_check_kinds(old_checks)
            now = disabled_check_kinds(checks_path.read_text(encoding="utf-8"))
            head_text = checks_path.read_text(encoding="utf-8")
            was_on, now_on = (configured_check_kinds(old_checks),
                              configured_check_kinds(head_text))
            if (was is None or now is None
                    or was_on is None or now_on is None):
                readable = False
            else:
                if now - was:                       # newly set to `false`
                    removed[f"{PROJECT_CHECKS} (disabled)"] = sorted(now - was)
                deleted = was_on - now_on - now     # deleted, not disabled
                if deleted:
                    removed[f"{PROJECT_CHECKS} (kind deleted)"] = sorted(deleted)
        if readable:
            facts["removed_table_entries"] = removed

    if facts["changed_paths"] is not None and any(
            fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(Path(p).name, pat)
            for p in facts["changed_paths"] for pat in DEPENDENCY_FILES):
        facts["dependency_considered"] = True
        try:
            done = subprocess.run([sys.executable, str(root / "tools" / "deps.py")],
                                  capture_output=True, timeout=180, cwd=str(root),
                                  stdin=subprocess.DEVNULL,
                                  encoding="utf-8", errors="replace")
            facts["deps_exit"] = done.returncode
        except (OSError, subprocess.SubprocessError):
            facts["deps_exit"] = None

    return facts


def render(findings: list[dict], seen: list[str], base: str) -> str:
    fired = [f for f in findings if f["severity"] == "blocking"]
    unsure = [f for f in findings if f["severity"] == "unknown"]
    if not findings:
        return (f"security-gate: clean -- {len(seen)} clause(s) evaluated, 0 fired "
                f"(base {base})")
    waived = [f for f in findings if f["severity"] == "advisory"]
    head = f"security-gate: {len(fired)} fired, {len(unsure)} not evaluated"
    if waived:
        head += f", {len(waived)} waived"
    lines = [f"{head} (base {base})"]
    for f in findings:
        tag = "BLOCKING" if f["severity"] == "blocking" else f["severity"].upper()
        lines.append(f"  [{f['clause']}] {tag}: {f['finding']}")
        for d in f["detail"]:
            lines.append(f"      {d}")
    skipped = [c for c in CLAUSES if c not in seen]
    if skipped:
        lines.append(f"  not applicable to this diff: {', '.join(skipped)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="main",
                    help="the ref to compare against. No useful default exists "
                         "-- `main` is this repository's, name yours.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--offline", action="store_true",
                    help="gather nothing; every clause reports unknown")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    facts = gather_facts(root, args.base, offline=args.offline)
    findings = evaluate(facts)
    seen = considered(facts)
    if args.json:
        print(json.dumps({"findings": findings, "considered": seen,
                          "base": args.base, "exit": exit_code(findings)},
                         indent=2))
    else:
        print(render(findings, seen, args.base))
    return exit_code(findings)


if __name__ == "__main__":
    raise SystemExit(main())

"""Shared helpers for this repo's hook scripts.

Every hook here has two callers and must behave identically for both:

  Claude Code       registers the script directly in .claude/settings.json and
                    delivers the payload as JSON on stdin.
  a human           runs the script directly with the payload in the HOOK_PAYLOAD
                    env var, which is the documented way to test a hook after
                    editing it:

                        HOOK_PAYLOAD='{}' python .claude/hooks/<event>/<hook>.py

`load_payload()` accepts either, so a hook never cares which one invoked it. Both
paths are load-bearing -- CLAUDE.md requires a hook to be fired by hand before it
is trusted, because a broken hook's symptom is silence.

Not placed inside an event directory on purpose: anything that runs every file in
`.claude/hooks/<event>/` would run a helper module living there as though it were
a hook. The `_` prefix says the same thing to a reader.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent


# --- shared refusal rules ---------------------------------------------------
#
# One definition each, because two hooks now enforce them at different moments.
# `pre-commit/01-secret-scan.py` catches a commit the model is about to run;
# `post-run/06-artifact-autocommit.py` catches one it makes itself from a
# subprocess, which never passes through PreToolUse and so sees no gate at all.
# Two copies of these patterns would diverge, and the copy that diverged would
# be the one guarding the unattended path.

# Content patterns -- a credential pasted into a source file. Provider prefixes
# are taken from each vendor's published token format, the same basis gitleaks
# uses; they are high-signal because the prefix plus length is not something
# ordinary source contains by accident.
SECRET_PATTERNS = [
    # --- cloud
    re.compile(r"AKIA[0-9A-Z]{16}"),                          # AWS access key id
    re.compile(r"(?i)aws(.{0,20})?secret(.{0,20})?[\"'][0-9a-zA-Z/+]{40}[\"']"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),                    # Google API key
    # --- source hosts
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),                # GitHub PAT / OAuth / refresh
    re.compile(r"glpat-[A-Za-z0-9_\-]{20,}"),                 # GitLab PAT
    # --- payments and comms
    re.compile(r"(?:sk|rk)_live_[0-9a-zA-Z]{20,}"),           # Stripe live key
    re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"),             # Slack
    re.compile(r"SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}"),  # SendGrid
    re.compile(r"SK[0-9a-fA-F]{32}"),                         # Twilio
    # --- model providers
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),                # Anthropic
    re.compile(r"sk-[A-Za-z0-9]{32,}"),                       # OpenAI and lookalikes
    # --- package registries
    re.compile(r"npm_[A-Za-z0-9]{36}"),
    # --- key material and tokens
    re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PGP)? ?PRIVATE KEY( BLOCK)?-----"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\."),  # JWT
    # --- connection strings carrying inline credentials. The single highest
    # value pattern for a web app, and the one a prefix list never catches.
    re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://"
               r"[^\s:/@]+:[^\s:/@]+@"),
    # --- generic assignment, last because it is the noisiest
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*"
               r"[\"'][^\"']{8,}[\"']"),
]

# Path patterns -- files whose *existence* in a commit is the leak, whatever they
# contain. A `.env` holding a database DSN with inline credentials matches a
# content pattern above; one holding `STRIPE_KEY=<redacted-by-teammate>` does
# not, and both belong out of git. Shape borrowed from carlrannaberg/claudekit's
# sensitive-patterns.ts, which blocks by path for exactly this reason.
#
# No literal example DSN here on purpose: this file is itself scanned, and a
# realistic one in a comment made the repo uncommittable the moment the pattern
# was added. The same trap applies to `AKIA` and to any other prefix added below:
# write the pattern, never an instance of it.
#
# fnmatch semantics, matched against the repo-relative POSIX path and against the
# bare filename, so `id_rsa` matches at any depth.
SECRET_PATH_PATTERNS = [
    ".env", ".env.*",                                    # …but see SECRET_PATH_ALLOW
    "*.pem", "*.key", "*.crt", "*.cer", "*.p12", "*.pfx", "*.ppk",
    "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*",
    ".ssh/*", ".aws/*", ".azure/*", ".gcloud/*", ".kube/*",
    "*.keystore", "keystore", "truststore",
    ".npmrc", ".pypirc", ".netrc", ".authinfo", ".git-credentials", ".pgpass",
    "credentials.*", "secrets.*", "api-keys.*", "*.token", ".secrets",
    "wallet.dat", "wallet.json", "*.wallet", "seed.txt",
    "*.sqlite3", "dump.sql", "*.dump", "prod.db", "production.db",
    "terraform.tfvars", "*.tfstate",
    "serviceaccount*.json", "gcp-key.json",
]

# Templates are the point of committing an env file at all -- they document the
# variables without carrying values. Checked before SECRET_PATH_PATTERNS.
SECRET_PATH_ALLOW = [
    ".env.example", ".env.template", ".env.sample", ".env.dist",
    "*.pem.example", "*.example", "*.template", "*.sample",
]

# CLAUDE.md: "Never put AI attribution in git history." Enforced on the message
# an auto-commit generates, since no human reads it before it lands.
AI_ATTRIBUTION_PATTERNS = [
    re.compile(r"(?i)co-authored-by:\s*(claude|anthropic|gpt|copilot)"),
    re.compile(r"(?i)generated with \[?claude"),
    re.compile(r"(?i)\bwritten by (claude|an? ai\b)"),
    re.compile(r"(?i)🤖"),
]

PROTECTED_BRANCHES = {"main", "master", "develop", "release"}

# Database migrations are the least reversible thing a product contains: a
# dropped column is gone in a way a bad deploy is not, and no test suite in the
# world proves an `ALTER TABLE` was the right idea. The cited failure mode for
# coding agents is exactly this -- a syntactically valid migration written with
# no database to run it against.
#
# So they are never auto-committed. Not because writing one is wrong, but because
# it is the class of change that must not land while nobody is looking.
# Framework-agnostic: these are the conventional locations, not one ORM's.
MIGRATION_PATH_PATTERNS = [
    "migrations/*", "*/migrations/*", "**/migrations/*",
    "alembic/versions/*", "**/alembic/versions/*",
    "prisma/migrations/*", "**/prisma/migrations/*",
    "supabase/migrations/*", "db/migrate/*", "**/db/migrate/*",
    "**/*.migration.sql", "schema.sql", "**/schema.prisma",
]


def migration_paths(paths):
    """Those of `paths` that look like a schema migration."""
    import fnmatch
    hits = []
    for rel in paths:
        norm = str(rel).replace("\\", "/")
        while norm.startswith("./"):
            norm = norm[2:]
        if any(fnmatch.fnmatch(norm, pat) for pat in MIGRATION_PATH_PATTERNS):
            hits.append(rel)
    return hits


# Recovered from `05-docs-required.py` (deleted 2026-08-02, see `350dec2^`) and
# promoted here, because deleting that hook deleted the only correct
# implementation and the bug it documented came straight back: on 2026-08-03
# both surviving pre-commit hooks still used
#
#     re.compile(r"\bgit\s+(?:-[^\s]+\s+)*commit\b")
#
# which cannot match `git -C /repo commit` -- `-C` takes a value, and the
# repetition has no way to consume it. The branch guard therefore ignored every
# cross-repo commit, silently.
#
# The original docstring's reasoning, kept: a regex was tried first and got this
# wrong in both directions -- it missed `git -C /repo commit` and matched
# `git commit-tree`, because `\b` matches before a hyphen. Tokenising is clearer
# than the regex that would handle both.
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def is_git_commit(command: str) -> bool:
    """True for a real `git commit` invocation, false for lookalikes."""
    toks = command.split()
    for i, tok in enumerate(toks):
        if tok != "git" and not tok.endswith("/git"):
            continue
        j = i + 1
        while j < len(toks) and toks[j].startswith("-"):
            if toks[j] in VALUE_FLAGS:
                j += 1  # skip its value too
            j += 1
        if j < len(toks) and toks[j] == "commit":
            return True
    return False


# A command can commit into a repository that is not the session's:
#
#     cd ../other && git commit …
#     git -C ../other commit …
#
# Two hooks need this answer -- `02-branch-guard.py` to read the right branch and
# `03-attribution-guard.py` to read the right `user.name`. They each had their own
# regex for it, and the two disagreed: branch-guard's
#
#     r"\bgit\s+(?:-\w+\s+\S+\s+)*-C\s+..."
#
# assumed every global flag is `-x value`, so a BOOLEAN global (`--no-pager`,
# `-P`, `--paginate`, `--literal-pathspecs`) stopped the repetition and the `-C`
# after it was never seen. The guard then resolved the SESSION's repo and would
# have allowed a commit onto a sibling's protected `main` -- silently, and for
# the second time: the identical class of bug cost eight such commits on
# 2026-08-03, which is why `is_git_commit` above is a tokeniser and not a regex.
#
# So this is a tokeniser too, and there is one copy. Two implementations of "which
# repo does this command touch" is how the weaker one ends up guarding the
# unattended path.
CD_RE = re.compile(r"(?:^|&&|;|\|\|)\s*cd\s+(?:--\s+)?([\"']?)([^\s\"'&;|]+)\1")


def git_dash_c(command: str) -> str | None:
    """The last `git -C <dir>` target in a command, or None.

    Walks git's global-flag region the way git itself does: a flag consumes one
    extra token only when it is in `VALUE_FLAGS`. Boolean flags and
    `--flag=value` forms consume nothing extra, which is precisely what the old
    regex could not express.
    """
    toks = command.split()
    found = None
    for i, tok in enumerate(toks):
        if tok != "git" and not tok.endswith("/git"):
            continue
        j = i + 1
        while j < len(toks) and toks[j].startswith("-"):
            if toks[j] == "-C" and j + 1 < len(toks):
                found = toks[j + 1].strip("\"'")
            if toks[j] in VALUE_FLAGS:
                j += 1  # skip its value too
            j += 1
    return found


def git_target_dir(command: str, session_cwd: str) -> str:
    """The directory the command's git will actually run in.

    `git -C` wins over `cd`: it is applied per-invocation and overrides whatever
    directory the shell is in. Relative paths resolve against the last `cd` if
    there was one, otherwise against the session cwd -- the way the shell does it.

    A path that does not exist falls back to `session_cwd`, so a caller always
    gets a real directory to inspect rather than having to handle None.
    """
    def resolve(against: str, candidate: str) -> str:
        return (candidate if os.path.isabs(candidate)
                else os.path.join(against, candidate))

    base = session_cwd

    # The LAST cd is the one in effect when git runs: `cd a && cd b && git …`
    # commits in b.
    cds = CD_RE.findall(command)
    if cds:
        base = resolve(base, cds[-1][1])

    dash_c = git_dash_c(command)
    if dash_c:
        base = resolve(base, dash_c)

    return base if os.path.isdir(base) else session_cwd


def current_branch(repo_root=None):
    """The checked-out branch name, or None when git cannot answer.

    None means "cannot tell", never "not protected" -- callers must treat it as
    a refusal, not a pass. A detached HEAD returns 'HEAD', which is not in
    PROTECTED_BRANCHES and is correctly allowed: you cannot damage a branch you
    are not on.
    """
    root = Path(repo_root) if repo_root else HOOKS_DIR.parents[1]
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def secret_path_hit(rel):
    """True when a path is one that should never be committed, whatever it holds.

    Allowlist wins: `.env.example` documents the variables and carries no values,
    which is the whole reason to commit one.
    """
    import fnmatch
    norm = str(rel).replace("\\", "/")
    # NOT lstrip("./") -- that strips a *character set*, so ".env" becomes "env"
    # and the single most important pattern here silently stops matching. Caught
    # on 2026-08-02 by running it, and it was the second place in the repo to have
    # the identical bug that week, which is how often this one bites.
    while norm.startswith("./"):
        norm = norm[2:]
    name = norm.rsplit("/", 1)[-1]
    for pattern in SECRET_PATH_ALLOW:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(norm, pattern):
            return False
    for pattern in SECRET_PATH_PATTERNS:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(norm, pattern):
            return True
    return False


def scan_for_secrets(paths, repo_root=None):
    """Paths that are a credential risk, by name or by content.

    Two axes, because each misses what the other catches. A `.env` whose values a
    teammate already redacted matches no content pattern and still must not be
    committed; a key pasted into `app.py` has an innocuous path.

    Unreadable files are skipped for the content check but still judged on path.
    That is safe only because every caller refuses on any finding: a file that
    cannot be read cannot be shown to match, and the commit is a local checkpoint
    that has not left the machine.
    """
    root = Path(repo_root) if repo_root else HOOKS_DIR.parents[1]
    findings = []
    for rel in paths:
        if secret_path_hit(rel):
            findings.append(f"{rel} (path)")
            continue
        target = root / rel
        try:
            text = target.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(p.search(text) for p in SECRET_PATTERNS):
            findings.append(rel)
    return findings


def load_payload() -> dict:
    """Return the hook payload from HOOK_PAYLOAD or stdin, whichever is present.

    HOOK_PAYLOAD is checked FIRST, and the ordering is load-bearing, not a
    preference. run_hook.py launches hooks without redirecting stdin, so the
    child inherits the parent's stdin -- which, when the parent was itself
    launched from a pipe, is an open handle that never reaches EOF. Reading it
    blocks forever and hangs the whole run. `isatty()` does not save you: an
    inherited pipe is not a TTY, so the guard passes and the read still blocks.

    Checking the env var first means the only caller that leaves stdin dangling
    never reaches the stdin branch at all. Claude Code sets no HOOK_PAYLOAD and
    always writes real JSON to stdin, so it falls through correctly.
    """
    raw = os.environ.get("HOOK_PAYLOAD", "")

    if not raw.strip():
        try:
            if not sys.stdin.isatty():
                raw = sys.stdin.read()
        except Exception:
            raw = ""

    if not raw.strip():
        return {}

    try:
        data = json.loads(raw)
    except Exception:
        return {"raw": raw}
    return data if isinstance(data, dict) else {"raw": data}


# `write_log(filename, prefix, payload)` lived here until 2026-08-03. It appended
# a JSON line to `HOOKS_DIR / filename` -- runtime output written into the source
# directory. Removed, and the hooks are stateless now, for three reasons:
#
#   1. Nothing ever read any of them. Twelve `.log` files had accumulated and
#      exactly two still had a writer; the other ten were residue of the 19 hooks
#      deleted 2026-08-02, indistinguishable from live files.
#   2. Claude Code already logs hooks properly. `claude --debug-file <path>`, or
#      `/debug` mid-session, records which hooks matched, their exit codes,
#      stdout and stderr. `error.log`, `pre-run.log`, `post-run.log` and
#      `session-start.log` were hand-rolling a worse version of that.
#   3. The payloads were session transcripts. They captured prompt text and tool
#      input verbatim, which is why `.gitignore` had to promise they would never
#      be committed -- and why `install.py` was copying 3.5 MB of one repo's
#      prompts into every target it touched.
#
# A GitHub code search for `write_log` under `path:.claude/hooks` returns zero
# results. The two published hook collections either keep the directory
# scripts-only with logs elsewhere, or are stateless like this.
#
# If a hook ever needs to persist something, `state/` is the place: it is
# gitignored wholesale and already excluded by the installer.


def command_of(payload: dict) -> str:
    """The shell command for a tool-related payload, or '' for anything else."""
    tool_input = payload.get("tool_input") or {}
    return tool_input.get("command") or "" if isinstance(tool_input, dict) else ""


def deny(reason: str, event: str = "PreToolUse") -> None:
    """Block the pending action. Only meaningful on PreToolUse."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def ask(reason: str, event: str = "PreToolUse") -> None:
    """Interrupt for a yes/no. Use when the action is legitimate but needs a human
    to confirm the scope -- `deny` would be wrong because there is a correct way to
    proceed. `pre-commit/03-review-gate.py` carried its own copy of this until
    2026-08-02."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


# The index baseline, the turn-scoped doc snapshot and the transcript/sign-off
# readers were removed on 2026-08-02 along with the hooks that were their only
# consumers (`03-index-baseline`, `06-index-scope-guard`, `04-docs-staleness`,
# `05-docs-gate`, `03-review-gate`, `04-delivery-guard`). They are in `350dec2`
# and the commit that follows it. Do not reintroduce one speculatively: each
# existed to answer a question some gate asked, and the gates are gone.

KNOWLEDGE_DOCS = {"LOG.md", "HANDOFF.md", "TASK.md", "MEMORY.md", "ISSUES.md"}


def changed_paths(repo_root=None):
    """Paths git reports as changed, or None when git cannot answer.

    The single source of truth for "what did this turn touch".
    `post-run/06-artifact-autocommit.py` commits exactly this set, so a second
    near-copy of this parsing would decide what gets committed the first time the
    two diverged.
    """
    root = Path(repo_root) if repo_root else HOOKS_DIR.parents[1]
    try:
        # -uall, not the default -unormal: git otherwise collapses an untracked
        # directory to one entry (`?? docs/specs/`), which hides every file inside
        # it. `post-run/06-artifact-autocommit.py` saw no new spec at all until this
        # was fixed -- a brand-new artefact is exactly the collapsed case.
        proc = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            out.append(path)
    return out








# --- what kind of failure is this ------------------------------------------
#
# The autocommit hook counted every red check identically: it hashed the failing
# output and spent one of three repair attempts. So a port collision, a locked
# file on Windows, or a registry hiccup burned the same budget as a real type
# error, and escalated with the same words -- while "repairing" infrastructure
# noise means editing product code to chase a fault that is not in it.
#
# The fix is to decide the KIND before spending anything, and to decide it from
# a data table rather than a judgement. Same shape as `_projectchecks.MARKER_CHECKS`:
# a new ecosystem, or a new flavour of noise, is a row.
#
# Order is priority, first match wins, and the order is the policy:
#
#   security      never retried, never auto-repaired, budget 0
#   merge         fixed by rebasing onto the current target, not by editing files
#   deterministic a real defect -- repaired on a budget
#   transient     infrastructure -- retried, and product code is left alone
#   unknown       treated as deterministic, because guessing "noise" would
#                 retry a real bug forever
#
# deterministic outranks transient deliberately. Output carrying both an
# assertion failure and a network warning is a real failure that happened to
# mention the network; classifying it the other way retries until the budget is
# gone and changes nothing.
FAILURE_CLASSES = [
    # --- security -----------------------------------------------------------
    (re.compile(r"(?i)\b(?:secret|credential|api[_-]?key|token)s?\b[^\n]{0,60}"
                r"\b(?:detected|found|leaked|exposed|would be committed)\b"),
     "security", "block"),
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"),
     "security", "block"),
    (re.compile(r"\bCVE-\d{4}-\d{4,}\b"), "security", "block"),
    (re.compile(r"(?i)\b(?:critical|high)\s+severity\s+vulnerabilit"),
     "security", "block"),

    # --- merge --------------------------------------------------------------
    (re.compile(r"CONFLICT \([^)]+\)"), "merge", "rebase"),
    (re.compile(r"(?i)automatic merge failed"), "merge", "rebase"),
    (re.compile(r"(?i)\bneeds rebase\b"), "merge", "rebase"),

    # --- deterministic ------------------------------------------------------
    (re.compile(r"\berror TS\d+\b"), "deterministic", "repair"),          # tsc
    (re.compile(r"\berror\[E\d+\]"), "deterministic", "repair"),          # rustc
    (re.compile(r"\b(?:Syntax|Import|ModuleNotFound|Name|Type|Attribute|Value|Key|Index)"
                r"Error\b"), "deterministic", "repair"),
    (re.compile(r"\bAssertionError\b"), "deterministic", "repair"),
    (re.compile(r"(?m)^FAILED\s"), "deterministic", "repair"),            # pytest
    (re.compile(r"(?i)\b\d+ (?:tests? )?failed\b"), "deterministic", "repair"),
    (re.compile(r"(?i)\bexpected\b[^\n]{0,40}\bto (?:be|equal|contain|match)\b"),
     "deterministic", "repair"),
    (re.compile(r"(?i)\bundefined: \w+"), "deterministic", "repair"),     # go
    (re.compile(r"(?i)\bcannot find (?:name|module|symbol|package)\b"),
     "deterministic", "repair"),
    # `path:line:col: CODE message` -- ruff, flake8, eslint --format=compact
    (re.compile(r"(?m)^\S+:\d+:\d+: [A-Z]+\d+\b"), "deterministic", "repair"),

    # --- transient ----------------------------------------------------------
    (re.compile(r"\b(?:ECONNRESET|ETIMEDOUT|ECONNREFUSED|EAI_AGAIN|ENOTFOUND)\b"),
     "transient", "retry"),
    (re.compile(r"\b(?:EADDRINUSE|EBUSY|EAGAIN|EMFILE|ENFILE)\b"), "transient", "retry"),
    (re.compile(r"(?i)address already in use"), "transient", "retry"),
    (re.compile(r"(?i)\brate limit(?:ed|ing)?\b|\b429 too many requests\b"),
     "transient", "retry"),
    (re.compile(r"(?i)could not resolve host|temporary failure in name resolution"),
     "transient", "retry"),
    (re.compile(r"(?i)resource temporarily unavailable"), "transient", "retry"),
    (re.compile(r"(?i)being used by another process"), "transient", "retry"),  # Windows
    (re.compile(r"(?i)connection reset by peer|network is unreachable"),
     "transient", "retry"),
    (re.compile(r"(?i)\b(?:read|connect|handshake) timed out\b"), "transient", "retry"),
    # subprocess.TimeoutExpired, pytest-timeout, `timed out after Ns`. A command
    # that normally finishes in a quarter of a second and then blows a 30s limit
    # did not become wrong -- the machine got busy. Classifying this as a defect
    # spends a repair budget editing code that was never at fault, which is the
    # exact waste this table exists to prevent. Added 2026-08-07 after
    # `test_session_start_contract.py` timed out behind twenty other suites.
    (re.compile(r"(?i)TimeoutExpired|\btimed out\b|\btimeout expired\b"),
     "transient", "retry"),
]

# How many times each kind may be attempted before the ladder escalates.
#
# security is 0 on purpose: a credential in a diff is not a thing to have another
# go at. transient is lower than deterministic because a retry is nearly free and
# a third identical network failure is not noise any more -- it is an outage, and
# an outage is a human's problem, not a repair loop's.
FAILURE_BUDGETS = {
    "security": 0,
    "merge": 2,
    "transient": 2,
    "deterministic": 3,
    "unknown": 3,
}

DEFAULT_FAILURE_CLASS = ("unknown", "repair")


def classify_failure(detail: str) -> tuple[str, str]:
    """(class, action) for a failing check's output. Never raises.

    Unmatched output is `("unknown", "repair")` rather than anything cheaper:
    the expensive mistake is calling a real defect noise, so the default is the
    one that investigates.
    """
    if not detail:
        return DEFAULT_FAILURE_CLASS
    for pattern, kind, action in FAILURE_CLASSES:
        if pattern.search(detail):
            return kind, action
    return DEFAULT_FAILURE_CLASS


def failure_budget(kind: str) -> int:
    """Attempts allowed for a class before the ladder escalates."""
    return FAILURE_BUDGETS.get(kind, FAILURE_BUDGETS["unknown"])


def failure_signature(detail: str) -> str:
    """A stable key for "the same failure again".

    Digits are stripped before hashing: a suite reporting `3 failed` then
    `2 failed` is the same failure getting closer, not a new one, and counting
    them separately would reset the attempt budget on every partial fix.

    Lived in `post-run/06-artifact-autocommit.py` until the loop needed it too.
    One definition, because two would diverge and the diverged copy would be the
    one deciding when to give up.
    """
    import hashlib
    normalised = re.sub(r"\d+", "#", detail)
    return hashlib.sha256(normalised.encode("utf-8", "replace")).hexdigest()[:12]


# --- reading what the user actually said ----------------------------------
#
# The PreToolUse payload carries `transcript_path`, a JSONL file of the whole
# session. Hooks can therefore check whether the user really authorised
# something instead of guessing -- `04-delivery-guard.py` claimed the opposite
# ("only has the current Bash call, not conversation history") until 2026-08-02.
# Technique adapted from 011matthias/agentic-ops1.01's no-auto-commit-gate.py.
#
# Everything here fails open: an unreadable transcript yields no messages, and
# every caller must treat "no messages" as "no authorisation found" rather than
# as permission.


# The harness writes this exact prefix into a tool_result when the user picks an
# AskUserQuestion option. It is the only tool output treated as user speech.












# --- what the capability layer owns, in a repository it was installed into ---
#
# The defect this closes, found end-to-end on 2026-08-07 by installing into a
# synthetic inherited repo and reading the output: `tools/recon.py` reported "25
# test files over 26 code files (ratio 0.962)" for a repository whose own source
# was a single file. It was counting the layer's own `tools/test_*.py`. Same root
# cause made `install.py --dry-run` say "empty -- start at task-brief" and the
# post-install report say "an existing codebase", and it would have pushed
# `resume.py` into RECON on a two-file repo.
#
# Three readings of the host repository, all inflated by the guest. A layer that
# measures itself and calls the number the host's is worse than one that measures
# nothing, because every judgement downstream inherits it.
#
# Pattern-matching `tools/` was the obvious fix and is wrong: a host repository
# may have its own `tools/`, and the installer merges into it. So the installer
# records exactly what it wrote, and this reads that record back. Absent manifest
# means nothing is excluded -- which is correct in the source repo, where the
# layer IS the repository.
LAYER_MANIFEST = ".claude/layer-manifest.json"


def layer_paths(root):
    """The repo-relative posix paths this layer installed, or an empty set.

    Fails open to empty: an unreadable or malformed manifest must not hide the
    host's own files from a measurement. Over-reporting the host's code is a
    recoverable inconvenience; under-reporting it is a wrong answer that looks
    right.
    """
    import json as _json
    import os as _os
    path = _os.path.join(str(root), *LAYER_MANIFEST.split("/"))
    try:
        with open(path, encoding="utf-8") as fh:
            data = _json.load(fh)
    except Exception:
        return set()
    paths = data.get("paths") if isinstance(data, dict) else None
    if not isinstance(paths, list):
        return set()
    return {str(p).replace("\\", "/") for p in paths}

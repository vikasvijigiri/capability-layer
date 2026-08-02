"""Shared helpers for this repo's hook scripts.

Every hook here has two callers and must behave identically for both:

  Claude Code       registers the script directly in .claude/settings.json and
                    delivers the payload as JSON on stdin.
  a validator       runs `python tools/run_hook.py <event> '<json>'`, which
                    delivers the payload in the HOOK_PAYLOAD env var. CLAUDE.md
                    requires validators to do this, so it cannot be dropped.

`load_payload()` accepts either, so a hook never cares which one invoked it.

Not placed inside an event directory on purpose: run_hook.py executes every
file in `.claude/hooks/<event>/`, so a helper module living there would be
run as though it were a hook.
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
# was added. `tools/test_hooks.py` documents the same trap for `AKIA`.
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
    # on 2026-08-02 by running it; the identical bug had just been fixed in
    # tools/test_referenced_paths.py, which is how often this one bites.
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


def write_log(filename: str, prefix: str, payload) -> None:
    """Append one line to a log beside this module.

    The path is absolute. The original versions of these hooks wrote to
    './.claude/hooks/*.log', which silently scattered logs into whatever
    directory the caller happened to be in.
    """
    try:
        with (HOOKS_DIR / filename).open("a", encoding="utf-8") as handle:
            handle.write(f"{prefix}: {json.dumps(payload)}\n")
    except Exception:
        pass


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

KNOWLEDGE_DOCS = {"LOG.md", "HANDOFF.md", "TASK.md", "PLAN.md", "MEMORY.md", "ISSUES.md"}


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











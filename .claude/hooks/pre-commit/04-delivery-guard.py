"""
PreToolUse hook — global, fires only on Bash calls that look like a git/gh
delivery action (commit, push, merge, gh pr create, gh release create).

Scope, by design: fast, deterministic, mechanical checks only (secret
patterns, obvious debug statements, stray temp/local-env files,
protected-branch detection). It cannot
judge SOLID/DRY/architecture/commit-message quality -- that needs actual
reasoning about the diff's content, which the model must do itself before
attempting the delivery action. No skill owns that review; it was deleted in
the 2026-08-01 teardown and not replaced. This script is the deterministic
safety net underneath that judgment call, not a replacement for it.

Decision rules:
- Secrets/credentials found in the pending diff -> hard `deny`. This is the
  one case where overriding the user's own permission settings is
  justified: a leaked credential is worse than a false positive.
- Soft findings (debug statements, direct-to-protected-branch) -> no
  `permissionDecision` at all, just `additionalContext`. Setting
  `permissionDecision: "allow"` would *skip* the normal permission prompt,
  which would violate "always require explicit user approval before any
  remote git operation" -- so soft findings must never set that field.
- push / merge / gh pr create / gh release create (all "leaves the
  machine" actions) -> force `permissionDecision: "ask"` (unless already
  denied for secrets), so a broader Bash auto-approve setting can never
  silently push/merge/publish/release. Plain `commit` is local, so it only
  gets the checks, not the forced ask.
- Exception, narrow and path-scoped: a repo under ~/mvp-builds/<slug>/ is an
  autonomous-build workspace, freshly created per run, never an existing/shared
  repo -- the forced `ask` above is skipped there, since an unattended run has no
  human to answer it. Everywhere else this is completely unchanged. The
  secret-scan `deny` is NOT part of this exception -- it stays universal and
  non-negotiable in every repo, including this one.
  (The skill that created those workspaces was deleted on 2026-08-01. The path
  check is inert until something writes to ~/mvp-builds again, not wrong.)
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from _hooklib import load_payload as _load_payload  # noqa: E402

import json
import os
import re
import subprocess
import sys


MVP_BUILDS_ROOT = os.path.normcase(os.path.normpath(os.path.expanduser("~/mvp-builds")))


def is_autonomous_build_workspace(cwd):
    try:
        norm_cwd = os.path.normcase(os.path.normpath(os.path.abspath(cwd)))
        return norm_cwd.startswith(MVP_BUILDS_ROOT + os.sep) or norm_cwd == MVP_BUILDS_ROOT
    except Exception:
        return False


GIT_ACTION_PATTERNS = {
    "commit": re.compile(r"\bgit\s+commit\b"),
    "push": re.compile(r"\bgit\s+push\b"),
    "merge": re.compile(r"\bgit\s+merge\b"),
    "pr_create": re.compile(r"\bgh\s+pr\s+create\b"),
    "release": re.compile(r"\bgh\s+release\s+create\b"),
}

REMOTE_ACTIONS = {"push", "merge", "pr_create", "release"}

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "an AWS access key ID"),
    (re.compile(r"-----BEGIN(?:\s+RSA|\s+EC|\s+OPENSSH|\s+DSA)?\s*PRIVATE KEY-----"), "a private key block"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "a GitHub personal access token"),
    (re.compile(r"gh[oprsu]_[A-Za-z0-9]{30,}"), "a GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "a Slack token"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "an API-style secret key (sk-...)"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"][A-Za-z0-9/+=_\-]{12,}['\"]"), "a hardcoded credential-like assignment"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "a JWT-shaped token"),
]

# Tool-agnostic on purpose: the rule is "no AI/agent attribution," not "no Claude
# specifically" -- covers whichever tool actually wrote the commit/PR/release text.
#
# These match against the WHOLE command string and the hit is a hard `deny`, so a
# false positive is unrecoverable in-session -- precision matters more here than in
# a pattern that merely warns. The vendor names appear constantly as ordinary
# identifiers (a `~/.claude/` path, the `CLAUDE.md` filename, a `claude-sonnet-5`
# model id, the `anthropic` pip package, the `claude.ai` domain); none of those is
# attribution. The lookarounds below flag the word only when it stands alone as an
# actor, never when it is a path segment, filename, hyphenated id, or domain.
_STANDALONE = r"(?i)(?<![\w./@-]){}(?![\w./-])"

AI_ATTRIBUTION_PATTERNS = [
    re.compile(_STANDALONE.format("claude")),
    re.compile(_STANDALONE.format("codex")),
    # "anthropic" alone is too common as a package/vendor mention to flag; only its
    # attribution shapes are. Same reasoning applied one level tighter.
    re.compile(r"(?i)@anthropic\.com"),
    re.compile(r"(?i)\bby\s+anthropic\b"),
    re.compile(r"(?i)co-authored-by:\s*(claude|anthropic|codex|copilot|chatgpt|gemini|cursor)"),
    re.compile(r"(?i)generated\s+with\s+(claude|codex|copilot|chatgpt|gpt-\d|gemini|cursor)"),
    re.compile(r"(?i)\bgithub\s+copilot\b"),
    re.compile(r"🤖"),
]

DEBUG_PATTERNS = [
    re.compile(r"^\+.*\bconsole\.log\(", re.MULTILINE),
    re.compile(r"^\+.*\bdebugger;", re.MULTILINE),
    re.compile(r"^\+.*\bpdb\.set_trace\(\)", re.MULTILINE),
    re.compile(r"^\+.*\bbreakpoint\(\)", re.MULTILINE),
    re.compile(r"^\+.*\bbinding\.pry\b", re.MULTILINE),
]

JUNK_FILENAME_PATTERNS = [
    re.compile(r"(?i)\.(tmp|temp|bak|swp|orig)$"),
    re.compile(r"(?i)^\.ds_store$"),
    re.compile(r"(?i)^thumbs\.db$"),
    re.compile(r"(?i)\.pyc$"),
]
ENV_FILE_PATTERN = re.compile(r"(?i)(^|/)\.env(\.[a-z0-9_-]+)?$")
ENV_SAFE_SUFFIXES = (".example", ".sample", ".template", ".local.example")

PROTECTED_BRANCHES = {"main", "master"}


def run_git(args, cwd):
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        return result.stdout or ""
    except Exception:
        return ""


def detect_action(command):
    for name, pattern in GIT_ACTION_PATTERNS.items():
        if pattern.search(command):
            return name
    return None


def gather_diff(action, cwd):
    if action == "commit":
        return run_git(["diff", "--cached"], cwd)
    if action == "push":
        diff = run_git(["diff", "@{u}..HEAD"], cwd)
        return diff or run_git(["diff", "HEAD~5..HEAD"], cwd)
    if action in ("pr_create", "release"):
        for base in ("origin/HEAD...HEAD", "origin/main...HEAD", "origin/master...HEAD"):
            diff = run_git(["diff", base], cwd)
            if diff:
                return diff
        return ""
    return ""  # merge: no pending diff to inspect cheaply before it runs


def gather_changed_files(action, cwd):
    if action == "commit":
        out = run_git(["diff", "--cached", "--name-only"], cwd)
    elif action == "push":
        out = run_git(["diff", "--name-only", "@{u}..HEAD"], cwd) or run_git(
            ["diff", "--name-only", "HEAD~5..HEAD"], cwd
        )
    elif action in ("pr_create", "release"):
        out = ""
        for base in ("origin/HEAD...HEAD", "origin/main...HEAD", "origin/master...HEAD"):
            out = run_git(["diff", "--name-only", base], cwd)
            if out:
                break
    else:
        out = ""
    return [line.strip() for line in out.splitlines() if line.strip()]


def find_junk_files(files):
    findings = []
    for path in files:
        name = path.rsplit("/", 1)[-1]
        if any(pattern.search(name) for pattern in JUNK_FILENAME_PATTERNS):
            findings.append(path)
        elif ENV_FILE_PATTERN.search(path) and not name.lower().endswith(ENV_SAFE_SUFFIXES):
            findings.append(path)
    return findings


def find_secrets(diff):
    findings = []
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(diff):
            findings.append(label)
    return findings


def find_debug_statements(diff):
    for pattern in DEBUG_PATTERNS:
        if pattern.search(diff):
            return True
    return False


def find_ai_attribution(command):
    """Scan the whole command string (not just an extracted -m/--body argument) so
    heredocs, -F files-with-message, --title, and --body are all caught the same way."""
    for pattern in AI_ATTRIBUTION_PATTERNS:
        if pattern.search(command):
            return pattern.pattern
    return None


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def force_ask(note):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "additionalContext": note,
        }
    }))


def soft_note(note):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": note,
        }
    }))


def main():
    try:
        data = _load_payload()
    except Exception:
        return

    # PowerShell is the primary shell on Windows, so git/gh routed through the
    # PowerShell tool must be gated identically -- otherwise the delivery guard is
    # trivially bypassed on that platform.
    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return

    command = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or os.getcwd()

    action = detect_action(command)
    if action is None:
        return

    diff = gather_diff(action, cwd)
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd).strip()

    secrets = find_secrets(diff)
    if secrets:
        reason = (
            f"Git Delivery Guard blocked this {action}: the pending diff appears to contain "
            + ", ".join(secrets)
            + ". Remove it from the change before proceeding (and rotate it if it was ever exposed)."
        )
        deny(reason)
        return

    attribution = find_ai_attribution(command)
    if attribution:
        deny(
            f"Git Delivery Guard blocked this {action}: the commit/PR/release text "
            f"appears to contain an AI/agent-attribution reference (matched "
            f"'{attribution}'). Rewrite the message without it -- this repo's policy "
            f"is no AI attribution in git history, ever, regardless of which tool wrote it."
        )
        return

    soft_notes = []
    if action == "commit":
        # Unconditional, every commit. Diff review is model judgment, and that
        # judgment already failed once in practice (a commit went through with
        # no review at all). This hook has no way to *verify* review happened --
        # it only has the current Bash call, not conversation history -- so it
        # can't gate on that the way the secret-scan deny does. What it CAN do
        # is make sure the option is never silently forgotten.
        soft_notes.append(
            "this hook cannot verify whether the diff was reviewed -- "
            "if it hasn't, run it before proceeding"
        )
    if find_debug_statements(diff):
        soft_notes.append("the diff contains what looks like a leftover debug statement (console.log/debugger/pdb.set_trace/breakpoint)")
    junk_files = find_junk_files(gather_changed_files(action, cwd))
    if junk_files:
        soft_notes.append(
            "this change stages what looks like a temp/generated or local-env file: "
            + ", ".join(junk_files)
        )
    if branch in PROTECTED_BRANCHES and action in ("commit", "push"):
        soft_notes.append(f"this {action} targets '{branch}' directly")
    if action == "push" and re.search(r"--force\b|-f\b", command):
        soft_notes.append("this push uses --force, which can overwrite remote history")

    note_text = None
    if soft_notes:
        note_text = "Git Delivery Guard notes (non-blocking): " + "; ".join(soft_notes) + ". Confirm these are intentional."

    if action in REMOTE_ACTIONS and not is_autonomous_build_workspace(cwd):
        force_ask(note_text or f"Git Delivery Guard: {action} leaves the local machine -- explicit approval required.")
    elif note_text:
        soft_note(note_text)
    # else: clean commit/remote-action-in-an-mvp-builds-workspace, no findings -- allow silently


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

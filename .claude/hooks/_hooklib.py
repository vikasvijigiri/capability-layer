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


# --- session-scoped index baseline ------------------------------------------
#
# Staging is the one step in the whole chain with no guard on it, which is how 50
# files staged in earlier sessions sat in this repo's index for days waiting to be
# swept into an unrelated commit. Nothing in git distinguishes "I staged this just
# now" from "someone staged this on Tuesday" -- so the baseline is recorded at
# SessionStart, and anything in it that is *still* staged at commit time is a file
# the current session never chose.

INDEX_BASELINE = HOOKS_DIR / "state" / "index-baseline.json"


def staged_paths(repo_root=None):
    """Paths currently staged, sorted. None when git cannot answer."""
    root = Path(repo_root) if repo_root else HOOKS_DIR.parents[1]
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return sorted(p.strip().strip('"') for p in proc.stdout.splitlines() if p.strip())


def save_index_baseline(repo_root=None) -> None:
    """Record what was already staged when this session began. Never raises."""
    try:
        INDEX_BASELINE.parent.mkdir(parents=True, exist_ok=True)
        INDEX_BASELINE.write_text(
            json.dumps({"staged": staged_paths(repo_root)}), encoding="utf-8")
    except Exception:
        pass


def load_index_baseline():
    """The session's inherited staged set, or None when unknown.

    None and [] mean different things and must not be collapsed: [] is "the index
    was clean when the session started", None is "we never found out". Only the
    first is evidence that everything staged now belongs to this session.
    """
    try:
        data = json.loads(INDEX_BASELINE.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    staged = data.get("staged")
    return staged if isinstance(staged, list) else None


# --- turn-scoped knowledge-doc snapshot -------------------------------------
#
# `pre-run/04-docs-staleness.py` records the docs' content at UserPromptSubmit;
# `post-run/05-docs-gate.py` compares at Stop. A digest change means this turn
# wrote them.
#
# This exists because the gate previously compared mtimes, which false-blocked
# three times on 2026-08-01 with the docs correctly written -- git's index
# refresh bumps working-file mtimes, and an uncommitted backlog keeps old ones
# forever. Content answers "was it written this turn"; timestamps only ever
# approximated it. See decisions/2026-08-01-docs-gate-compares-content.md.

TURN_MARKER = HOOKS_DIR / "state" / "docs-turn-marker.json"
TRACKED_DOCS = ("LOG.md", "HANDOFF.md")


def doc_digests(repo_root=None) -> dict:
    """sha256 per tracked knowledge doc. A missing file digests as '' , not an error."""
    import hashlib
    root = Path(repo_root) if repo_root else HOOKS_DIR.parents[1]
    out = {}
    for name in TRACKED_DOCS:
        try:
            out[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        except OSError:
            out[name] = ""
    return out


KNOWLEDGE_DOCS = {"LOG.md", "HANDOFF.md", "TASK.md", "PLAN.md", "MEMORY.md", "ISSUES.md"}


def changed_paths(repo_root=None):
    """Paths git reports as changed, or None when git cannot answer.

    One implementation on purpose. `post-run/05-docs-gate.py` compares the work
    set it sees against the one `save_turn_marker` recorded at the start of the
    turn; two near-copies of this parsing would make that comparison meaningless
    the first time they diverged.
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


def work_paths(repo_root=None):
    """Changed paths excluding the knowledge docs, sorted. None when git cannot answer."""
    paths = changed_paths(repo_root)
    if paths is None:
        return None
    return sorted(p for p in paths if p not in KNOWLEDGE_DOCS)


def save_turn_marker(repo_root=None) -> None:
    """Snapshot the docs AND the work set at the start of a turn. Never raises.

    The work set is what makes the Stop gate's trigger per-turn. Without it the
    gate compared a standing backlog against a per-turn doc check, so a turn that
    changed nothing still tripped it -- five times in one session on 2026-08-02.
    Stored as None, not [], when git cannot answer: the gate must be able to tell
    "no work at turn start" from "unknowable", and only the first excuses a turn.
    """
    try:
        data = doc_digests(repo_root)
        data["work"] = work_paths(repo_root)
        TURN_MARKER.parent.mkdir(parents=True, exist_ok=True)
        TURN_MARKER.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def load_turn_marker():
    """The snapshot, or None when there isn't a usable one (first turn, or corrupt)."""
    try:
        data = json.loads(TURN_MARKER.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


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

USER_TURN_LOOKBACK = 30

# The harness writes this exact prefix into a tool_result when the user picks an
# AskUserQuestion option. It is the only tool output treated as user speech.
ANSWER_ENVELOPE = "Your questions have been answered"


def find_transcript(cwd=None):
    """Newest transcript for this project, or None.

    For `--record`-style CLI entry points, which get no payload and so have no
    `transcript_path` handed to them.
    """
    # Claude Code derives the directory name from the project path, but the
    # mangling is lossy and case-inconsistent -- `FDE_Vikas` becomes `FDE-Vikas`,
    # and the drive letter's case varies between `C--` and `c--`. Reconstructing
    # it exactly is unreliable, so normalise BOTH sides to lowercase-alphanumeric
    # and compare.
    #
    # Exact equality, never a prefix or suffix match: the parent project
    # `...-Documents-FDE-Vikas` sits alongside `...-Documents-FDE-Vikas-Notes`,
    # so a loose match silently reads another project's transcript.
    def _norm(value):
        return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")

    try:
        want = _norm(Path(cwd or os.getcwd()).resolve())
        base = Path.home() / ".claude" / "projects"
        for d in base.iterdir():
            if d.is_dir() and _norm(d.name) == want:
                sessions = list(d.glob("*.jsonl"))
                if sessions:
                    return str(max(sessions, key=lambda p: p.stat().st_mtime))
        return None
    except Exception:
        return None


def recent_user_messages(transcript_path, lookback=USER_TURN_LOOKBACK):
    """Text of the most recent user turns, newest first. [] on any failure.

    Harness text is stripped before returning: `<system-reminder>` blocks and
    `Stop hook feedback:` lines are injected by the runtime, not typed by the
    user, so treating them as authorisation would let a hook's own output
    authorise the thing it is gating.
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return []
    out = []
    try:
        with open(transcript_path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                msg = obj.get("message")
                if (obj.get("type") or (msg or {}).get("role")) != "user":
                    continue
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    parts = [content]
                elif isinstance(content, list):
                    parts = []
                    for b in content:
                        if not isinstance(b, dict):
                            continue
                        if b.get("type") == "text":
                            parts.append(b.get("text", ""))
                        elif b.get("type") == "tool_result":
                            # Tool results are command output, NOT the user
                            # speaking -- counting them would let the word
                            # "commit" inside any file grep authorise a commit.
                            # The one exception is an AskUserQuestion answer,
                            # which the harness writes only when the user
                            # actually clicked an option. That envelope is the
                            # strongest authorisation signal available.
                            #
                            # STARTSWITH, never "in". The envelope must be the
                            # whole message, not a substring of it. With `in`,
                            # any Bash output that merely mentioned the phrase
                            # counted as a user click -- caught 2026-08-02 when
                            # a debugging command printed the envelope and
                            # thereby authorised its own commit. Command output
                            # is attacker-adjacent input: a file, a grep hit or
                            # a log line can contain any text at all.
                            body = b.get("content")
                            if isinstance(body, str) and \
                                    body.lstrip().startswith(ANSWER_ENVELOPE):
                                parts.append(body)
                else:
                    continue
                text = "\n".join(p for p in parts if p)
                if text.strip():
                    out.append(text)
    except Exception:
        return []
    return list(reversed(out))[:lookback]


def nl_join(items):
    """Each answer on its own line, so head-of-line matching applies per answer."""
    return chr(10).join(items)


def _strip_harness(text: str) -> str:
    text = re.sub(r"<system-reminder>.*?</system-reminder>", " ", text, flags=re.S)
    text = re.sub(r"^Stop hook feedback:.*$", " ", text, flags=re.M)
    text = re.sub(r"^Called the \w+ tool with.*$", " ", text, flags=re.M)

    # An AskUserQuestion result reads: ..."<question>"="<answer>", "<q2>"="<a2>".
    # Only the ANSWERS are the user's choice; the questions are text I wrote.
    # Scanning the whole envelope let a question like "Who does the reviewing?"
    # with the option "I review, you approve" register as a sign-off on an
    # unrelated diff -- observed 2026-08-02, and it would have recorded a receipt
    # the user never gave. Reduce the envelope to its answer values.
    if ANSWER_ENVELOPE in text:
        answers = re.findall(r'=\s*\\?"(.*?)\\?"(?=\s*[,.]|\s*$)', text)
        text = nl_join(answers) if answers else " "
    return text


def authorization_in(messages, patterns, max_turns=None, head_words=None):
    """First user phrase matching any pattern, or None.

    `patterns` are regex strings, matched case-insensitively. Scanning stops
    after `max_turns` messages when given -- a tight window is right for
    "did they approve THIS", a wide one for "did they pre-authorise the session".

    `head_words` requires the match to fall within the first N words of a line.
    An approval leads with its decision ("Approve and record", "yes, go ahead");
    an incidental mention does not. Without it, the AskUserQuestion option label
    "I review, you approve" -- an answer about who reviews, chosen turns earlier
    for a different question -- registered as a sign-off and would have recorded
    a receipt the user never gave (2026-08-02). Position is the discriminator
    that wording alone could not supply.
    """
    for msg in messages[:max_turns] if max_turns else messages:
        scan = _strip_harness(msg)
        for line in scan.splitlines():
            head = line if head_words is None else " ".join(line.split()[:head_words])
            for pat in patterns:
                m = re.search(pat, head, re.I)
                if m:
                    return line.strip()[:120]
    return None

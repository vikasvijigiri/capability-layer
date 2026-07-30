"""
UserPromptSubmit hook — global, fires on every single user prompt.

Purpose: make "structure non-trivial tasks into a brief before executing"
a guaranteed reminder rather than something that depends on the model
remembering to invoke a skill. Skills are model-judgment-triggered, not
hook-triggered -- this hook exists specifically because that judgment
failed once already (see decisions/ for the incident this responds to).

Scope, by design: inject a short, fixed reminder string that points at the
`task-intake` skill. No classification of whether the prompt "is a task"
happens here (that needs real judgment, which a hook doesn't have), and no
attempt to carry out the restate/ask/approve loop itself -- a hook fires
once and can't hold a multi-step, stateful workflow across a turn; that
belongs in a skill, not here. This hook's only job is to make sure the
option to invoke `task-intake` is never silently forgotten.

One narrow, deterministic exception: an exact-match (after trimming/
lowercasing/stripping punctuation) common confirmation/continuation word --
"yes", "continue", "closed", etc. -- skips the injection entirely. This is
NOT judgment about whether a message "is a task" (a hook can't do that
reliably); it's a fixed wordlist match, cheap and unambiguous, for the one
case that was costing real tokens on every single turn including one-word
replies. Anything that isn't an exact match still gets the reminder --
err toward showing it, since a missed reminder is the failure mode this
hook exists to prevent.

Never blocks. Never delays. Fails open (top-level try/except; any error
means no additionalContext is added, prompt proceeds normally).

Revised once already for a related but distinct failure: an earlier version
of this hook told the model to itself restate the brief, get approval, AND
write TASK.md -- all inline in the reminder text. That conflated intent
capture with knowledge persistence in the same way the original gap
conflated "remembering a skill exists" with "doing the skill's job inline."
The fix both times is the same shape: keep this hook a single, short,
mechanical nudge, and let an actual skill (`task-intake`, then
`knowledge-manager`, then `workflow-orchestrator`) carry the real steps.
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from _hooklib import load_payload as _load_payload  # noqa: E402

import json
import re
import sys


REMINDER = (
    "This looks like it may be a new, non-trivial engineering task -- "
    "consider invoking `task-intake` to turn it into a structured, "
    "confidence-scored brief and get explicit approval before anything is "
    "logged or executed. Skip for trivial asks, direct questions, or "
    "continuations."
)

TRIVIAL_REPLIES = {
    "yes", "y", "no", "n", "ok", "okay", "k", "continue", "proceed", "done",
    "closed", "close", "thanks", "thank you", "go ahead", "sure", "yep",
    "yup", "correct", "approved", "approve", "sounds good", "looks good",
    "lgtm", "ack", "acknowledged", "got it", "understood", "resume", "next",
    "confirmed", "confirm", "continue please",
}


def extract_prompt_text(data):
    for key in ("prompt", "message", "user_prompt", "text"):
        value = data.get(key)
        if isinstance(value, str):
            return value
    return ""


def is_trivial_reply(text):
    normalized = re.sub(r"[.!?\s]+$", "", text.strip().lower())
    normalized = re.sub(r"^\s+", "", normalized)
    return normalized in TRIVIAL_REPLIES


def main():
    prompt_text = ""
    try:
        data = _load_payload()
        prompt_text = extract_prompt_text(data)
    except Exception:
        pass

    if prompt_text and is_trivial_reply(prompt_text):
        return  # exact-match trivial reply -- skip the injection, save the tokens

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": REMINDER,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

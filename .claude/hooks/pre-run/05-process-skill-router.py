"""pre-run -- matches the prompt against process-skill keywords and injects the result.

Why this exists
---------------
The skill listing is truncated against a token budget, so a skill's `description:`
-- its only other trigger surface -- can be absent on the exact turn it was needed.
This hook is the routing signal that survives that truncation: it matches the prompt
against `routing/process-skills.md` and injects the names of any skills that hit.

It replaced an earlier domain-prefix router that mapped keywords to a *name prefix*
(`frontend-`, `backend-`) rather than to a skill. That could never reach a skill
without a prefix, which is all of them now.

Observed failure, 2026-08-01: a request to brainstorm a research-tooling idea
matched the `research` capability (on the word "papers") and surfaced the
`research-` prefix. `brainstormer` -- the skill the request was actually asking
for -- was never named by any mechanism, because no mechanism could name it.

Scope, by design
----------------
Matching only, same contract as hook 02. It names skills that matched and says
they are invocable by name; it never invokes one, never reads a SKILL.md, and
never says what to do. Unlike hook 02 it names skills directly rather than a
prefix, because for these there is no prefix to name.

Word-boundary matching, not substring, so `retro` does not fire on
"retrospectively" beyond the tolerated plural. Multi-word keywords are matched as
phrases; entries in `process-skills.md` deliberately lean on phrases, since
naming a specific skill is a stronger claim than naming a domain.

Never blocks. Fails open -- any error means no context is injected and the turn
proceeds exactly as it would have.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTING = REPO_ROOT / ".claude" / "routing" / "process-skills.md"

# One phrase hit is enough. Entries here are multi-word by convention, so an
# incidental match is far less likely than it is for a single-word domain
# keyword -- the threshold that protects hook 02 is not needed here.
MIN_HITS_TO_REPORT = 1

# Beyond this the match is too diffuse to be a useful pointer, and listing more
# skills than the model will read is just injected noise.
MAX_SKILLS = 3


def load_process_skills():
    """Parse `.claude/routing/process-skills.md` into [(skill, [keyword, ...])].

    One `## <skill-name>` heading per entry, one `Keywords:` line beneath it.

    A heading is an entry only if it is a single whitespace-free token, so a
    prose section (`## Format contract`) is never mistaken for a skill. A heading
    with no `Keywords:` line is skipped: contributing zero keywords is
    observationally identical to being absent, and absent is the honest one.

    This parser does NOT check that the heading names a real skill directory --
    that is a repo-consistency question, not a per-turn one, and doing it here
    would put a filesystem walk on every prompt. `tools/test_process_router.py`
    asserts it instead.
    """
    try:
        text = ROUTING.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    entries = []
    for block in re.split(r"^## +", text, flags=re.M)[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        skill = lines[0].strip().lower()
        if not skill or len(skill.split()) != 1:
            continue
        match = re.search(r"^Keywords:\s*(.+)$", block, re.M)
        if not match:
            continue
        words = [k.strip().lower() for k in match.group(1).split(",") if k.strip()]
        if words:
            entries.append((skill, words))
    return entries


def keyword_pattern(word):
    """Word-boundary pattern for one keyword, tolerating a plural on the last word.

    Same rule as hook 02: people type "any ideas" and "bounce ideas", not the
    singular, and an exact match drops that on the floor. Applied only to the
    final word so leading words stay literal.
    """
    return r"(?<!\w)" + re.escape(word) + r"(?:e?s)?(?!\w)"


def hits_in(prompt_lower, words):
    """Keywords present in the prompt, matched on word boundaries."""
    return [w for w in words if re.search(keyword_pattern(w), prompt_lower)]


def main():
    payload = load_payload()
    prompt = payload.get("prompt") or payload.get("user_input") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return

    entries = load_process_skills()
    if not entries:
        return

    prompt_lower = prompt.lower()

    scored = []
    for skill, words in entries:
        matched = hits_in(prompt_lower, words)
        if len(matched) >= MIN_HITS_TO_REPORT:
            scored.append((len(matched), skill, matched))

    if not scored:
        return

    scored.sort(key=lambda row: (-row[0], row[1]))
    scored = scored[:MAX_SKILLS]

    # Deliberately terse. This fires on every matching turn, so every word here
    # is a recurring cost; the rationale for the mechanism belongs in this
    # module's docstring, which is never injected. One header, one line per
    # skill, no footer.
    lines = ["Process-skill keyword match (not a judgment — ignore if incidental):"]
    for _count, name, matched in scored:
        lines.append(f"- `{name}` — matched {', '.join(sorted(matched)[:2])}")

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines),
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

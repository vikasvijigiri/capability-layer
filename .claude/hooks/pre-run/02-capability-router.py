"""pre-run -- matches the prompt against capability keywords and injects the result.

Why this exists
---------------
CLAUDE.md's Capability Resolution Protocol asks the model to, on every single
turn, recall the protocol, list `.claude/capabilities/`, read nine `index.md`
files, fuzzy-match keywords, and only then act. That is prose, not a mechanism,
and it measurably does not happen: an audit of a ~25-turn session covering
broken MCP servers, a hanging test suite and hook failures -- all squarely
matching the `debugging` keyword list -- found zero capability index loads.

The 46 skills under `capabilities/*/skills/` are not discoverable by the Skill
tool either, because Claude Code reads `.claude/skills/<name>/SKILL.md` and
these live elsewhere by design. So nothing surfaces them automatically.

This hook closes that gap the same way `task_brief_nudge` closed it for
`task-intake`: UserPromptSubmit is the one event whose `additionalContext` is
injected straight into the turn, so a keyword match becomes something the model
is handed rather than something it must remember to go looking for.

Scope, by design
----------------
Matching only. It names the capability and the file to read; it never loads the
index, never picks a skill, and never says what to do. Choosing between a
blueprint, a workflow and a composed skill is judgment, and the index file
already documents that routing -- duplicating it here would create a second
place for it to drift.

Word-boundary matching, not substring: `az` must not fire on "amazing", and
`api` must not fire on "rapid". Multi-word keywords ("slow query", "background
job") are matched as phrases.

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
CAPABILITIES = REPO_ROOT / ".claude" / "capabilities"

# Below this, a match is more likely to be an incidental word than a real
# routing signal. One weak hit ("api" in passing) should not drag in a whole
# capability; two independent hits usually mean the topic is genuinely that one.
MIN_HITS_TO_REPORT = 1

# Beyond this many capabilities, the match is too diffuse to be informative and
# reporting all of them is just noise.
MAX_CAPABILITIES = 3


def keywords_for(index_path):
    try:
        text = index_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    match = re.search(r"^Keywords:\s*(.+)$", text, re.M)
    if not match:
        return []
    return [k.strip().lower() for k in match.group(1).split(",") if k.strip()]


def keyword_pattern(word):
    """Word-boundary pattern for one keyword, tolerating a plural on the last word.

    People type "add unit tests", not "add unit test", and an exact match drops
    that on the floor -- the single most common way a keyword list silently
    fails. Allowing an optional trailing `s`/`es` on the final word catches it
    without pulling in a stemmer. Applied only to the last word so that
    "background job" still matches "background jobs" but the leading words stay
    literal.
    """
    return r"(?<!\w)" + re.escape(word) + r"(?:e?s)?(?!\w)"


def hits_in(prompt_lower, words):
    """Keywords present in the prompt, matched on word boundaries."""
    found = []
    for word in words:
        if re.search(keyword_pattern(word), prompt_lower):
            found.append(word)
    return found


def main():
    payload = load_payload()
    prompt = payload.get("prompt") or payload.get("user_input") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return
    if not CAPABILITIES.is_dir():
        return

    prompt_lower = prompt.lower()

    scored = []
    for index_path in sorted(CAPABILITIES.glob("*/index.md")):
        matched = hits_in(prompt_lower, keywords_for(index_path))
        if len(matched) >= MIN_HITS_TO_REPORT:
            scored.append((len(matched), index_path.parent.name, matched))

    if not scored:
        return

    scored.sort(key=lambda row: (-row[0], row[1]))
    scored = scored[:MAX_CAPABILITIES]

    lines = [
        "Capability match (mechanical keyword scan of "
        ".claude/capabilities/*/index.md — not a judgment about what to do):"
    ]
    for count, name, matched in scored:
        shown = ", ".join(sorted(matched)[:6])
        lines.append(
            f"- **{name}** ({count} keyword{'s' if count != 1 else ''}: {shown}) "
            f"→ skills prefixed `{name}-` are in the Skill tool list; "
            f"read `.claude/capabilities/{name}/index.md` for routing"
        )
    lines.append(
        "The skills themselves are already discoverable by name — this only says "
        "which domain matched. Read the index when the work needs its routing: "
        "which blueprint or workflow takes precedence over composing skills, and "
        "which validator must run before any side effect. Ignore this block if "
        "the match is incidental."
    )

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

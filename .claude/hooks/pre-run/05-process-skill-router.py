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
# skills than the model will read is just injected noise. Caps keyword rows only
# -- the task-shape row below is added on top.
MAX_SKILLS = 3

# The skill the shape rule names. Not inlined, because the test suite asserts
# against this exact value and a typo would make every shape assertion vacuous.
TASK_SHAPE_SKILL = "task-brief"


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
    """Keywords present in the prompt, matched on word boundaries.

    A keyword that is contained in another *matched* keyword for the same skill
    is dropped, because the count is what `main()` sorts on and nesting inflates
    it. `research` lists both "use github" and "use github and see how people do
    it"; one phrase in the prompt scored 3 against two concepts, and with
    MAX_SKILLS truncating, a skill with more nested entries outranked one with
    more genuine matches. 19 such pairs exist across 11 of the 13 skills.

    The longer keyword is the one kept — it is the more specific claim, and it is
    what gets shown in the injected line.
    """
    found = [w for w in words if re.search(keyword_pattern(w), prompt_lower)]
    return [w for w in found
            if not any(other != w and w in other for other in found)]


# --- the task-shape rule -----------------------------------------------------
#
# Keywords cannot express "this prompt is asking for work". `task-brief` owns
# stage 1, but its keyword list can only name phrasings someone thought of, and
# real requests are phrased in ways nobody enumerates -- "Build an AI platform
# that assists scientists" hit nothing at all.
#
# So shape is consulted on EVERY turn: an imperative, or a request framing
# followed by a verb, is a task; a question about existing state is not.
#
# It was a FALLBACK until 2026-08-03 -- consulted only when no keyword matched --
# and that is why `task-brief` effectively never fired. One incidental phrase
# from any other skill's list suppressed it entirely, and the lists that compete
# on work requests are the long ones (`no-slop` 35 entries, `releasing` 27,
# `research` 23). Measured on real prompts: "Add a retry to the fetch call, the
# test fails without it" named `systematic-debugging` alone; "Add a healthcheck
# route so we can deploy this" named `releasing` alone. Both are stage-1
# requests carrying a stage-5+ phrase.
#
# The suite could not see it: `TASK_SHAPE_CASES` called `looks_like_a_task()`
# directly and never `main()`, so two of its own twelve task prompts routed to
# `no-slop` with every check green. It now asserts the injected output.
#
# Naming it ALONGSIDE rather than instead is the stated bias of this module,
# applied consistently: a false positive costs one line the model can ignore, a
# false negative costs the whole chain.

# Verbs that begin a work request. Present tense only -- "added support" is a
# report, "add support" is an ask.
TASK_VERBS = (
    "add|build|create|make|implement|write|fix|repair|refactor|rewrite|update|"
    "change|modify|remove|delete|drop|rename|move|migrate|port|wire|hook|"
    "integrate|generate|convert|extract|split|merge|enable|disable|support|"
    "improve|optimise|optimize|clean|tidy|set up|setup|configure|replace|"
    "introduce|expose|handle|cover|document|design|plan"
)

# Bare imperative: the prompt opens with the verb, possibly after filler.
# The filler list is not decoration -- "yes fix them" is a task and was missed
# because the prompt did not START with the verb.
IMPERATIVE_RE = re.compile(
    rf"^\s*(?:(?:please|now|also|then|and|so|ok|okay|sure|yes|yeah|next|"
    rf"first|finally)[\s,]+)*"
    rf"(?:{TASK_VERBS}|have|ensure|make sure|let us|let's)\b",
    re.IGNORECASE,
)

# A REQUIREMENT. This is the shape the first version missed entirely, and it is
# the most common way a person states work: not "add X" but "X should be Y".
# Four of six real prompts in one session were phrased this way --
# "all the skills should be repo agnostic", "it should be repo level".
#
# Safe because the question guard runs first: "should we split this?" is
# already excluded before this is consulted.
REQUIREMENT_RE = re.compile(
    r"\b(?:should|must|needs? to|has to|have to|ought to|supposed to)\b",
    re.IGNORECASE,
)

# Polite or first-person framing, with the verb close behind. The verb is
# required: "can you check the tests" is a question about state, "can you add a
# flag" is a task, and the verb list is what separates them.
# `can we` and friends are included even though they read as questions: the
# QUESTION_RE guard below already drops them when they actually end in `?`, so
# what survives is "can we have a hook that ..." -- a proposal, which is a task.
# That exact prompt was the heuristic's first miss.
#
# `have` and `get` earn a place only inside a framing, never as bare
# imperatives, because "can we have X" means create X while "have a look" does
# not.
FRAMED_RE = re.compile(
    rf"\b(?:can you|could you|would you|can we|could we|should we|shall we|"
    rf"please|i want|i'd like|i would like|i need|we need|we should|we want|"
    rf"let's|lets|help me|it should|there should be)"
    rf"\b[^.?!]{{0,40}}?\b(?:{TASK_VERBS}|have|get)\b",
    re.IGNORECASE,
)

# Asking about the world, not asking for a change. Checked first, because
# "why did X break" contains no task verb but "should we rename this" does.
QUESTION_RE = re.compile(
    r"^\s*(?:what|why|when|who|where|which|how come|is|are|was|were|does|do|"
    r"did|has|have|can we|should we|could we|would it)\b",
    re.IGNORECASE,
)


# Acknowledgements. Short enough to be caught by length alone in most cases,
# but "approved all" and "sounds good" are not, and neither asks for anything.
ACK_RE = re.compile(
    r"^\s*(?:yes|yeah|yep|ok|okay|sure|approved?|approve all|approved all|"
    r"continue|go ahead|done|thanks|thank you|good|sounds good|proceed|"
    r"looks good|lgtm)\b[\s.!]*$",
    re.IGNORECASE,
)


def looks_like_a_task(prompt: str) -> bool:
    """True when the prompt is asking for work rather than for an answer.

    Biased towards recall on purpose. A false positive costs one injected line
    that the model can ignore; a false negative costs the whole chain, because
    nothing else will suggest framing the work. The first version was tuned the
    other way and missed four of six real prompts in a single session.
    """
    text = prompt.strip()
    if len(text) < 8 or ACK_RE.match(text):
        return False
    # A question about existing state. Checked before everything else, so
    # "should we split this file?" never reaches the requirement rule.
    if QUESTION_RE.match(text) and text.rstrip().endswith("?"):
        return False
    return bool(
        IMPERATIVE_RE.match(text)
        or FRAMED_RE.search(text)
        or REQUIREMENT_RE.search(text)
    )


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

    scored.sort(key=lambda row: (-row[0], row[1]))
    scored = scored[:MAX_SKILLS]

    # Shape is consulted whether or not keywords matched, and adds a line rather
    # than replacing one. `MAX_SKILLS` caps the keyword rows only, so the worst
    # case is four lines, not three.
    named = {name for _count, name, _matched in scored}
    add_brief = TASK_SHAPE_SKILL not in named and looks_like_a_task(prompt)

    if not scored and not add_brief:
        return

    # Deliberately terse. This fires on every matching turn, so every word here
    # is a recurring cost; the rationale for the mechanism belongs in this
    # module's docstring, which is never injected. One header, one line per
    # skill, no footer.
    lines = ["Process-skill match (not a judgment — ignore if incidental):"]
    if add_brief:
        # First, because when it fires the others are usually incidental phrases
        # inside a request for work -- which is the whole finding.
        # Kept to one short line. The old wording was three clauses because it
        # fired only on the empty case; it now fires on most work turns, so its
        # length is a recurring cost rather than an occasional one.
        lines.append(f"- `{TASK_SHAPE_SKILL}` — shape, not keyword: this asks "
                     f"for work, and stage 1 owns it")
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

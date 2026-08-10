#!/usr/bin/env python3
"""user-prompt -- classifies the prompt's entry shape and lets workflow.md route it.

Fires on UserPromptSubmit, before the turn begins, so the entry rule is in
context on the turn that needs it rather than one turn late.

What it measures, and what it deliberately does not decide
----------------------------------------------------------
The measurement is "what shape is this prompt": does it name work with a
done-state, and is the approach settled or open. That is a text property, it is
deterministic, and a hook can do it on every turn without spending a token of
reasoning.

What that shape *means* is routing, and `.claude/workflow.md` **Entry** already
owns routing -- it is the file holding the table that says a settled approach and
an open one enter at different stages. So this script resolves a state key and
renders whatever that file says under the matching `[state:<key>]` block. Grep it
for the name of any skill and you will find none; delete every skill directory
and it still runs.

That shape is not a style preference. `pre-run/05-process-skill-router.py` did
the opposite -- a keyword table mapping phrases to hardcoded skill names -- and
was deleted on 2026-08-04 after it was pointed at a fabricated skill and every
suite in the repository passed. See
`decisions/2026-08-04-hooks-never-name-a-skill.md`.

A hook cannot invoke a skill
----------------------------
No hook output does that; the capability does not exist. This raises the entry
rule's visibility on a task-shaped turn, which is the ceiling, and saying so here
is more useful than implying a guarantee the mechanism cannot make.

Precedence, and why it is ordered this way
------------------------------------------
Five passes, first match wins, and the order carries the whole correctness
argument:

1. **Another stage owns it outright.** Diagnosis, planning, building, review,
   integration, release, evidence-gathering, surface design and layer
   maintenance all share vocabulary with framing prompts. They are checked first
   because a framing nudge on a diagnosis prompt is worse than silence -- it
   competes with the stage that should actually run.

   Those stages are described by what they do, never by the name of the skill
   that owns them, and that is a constraint rather than a style choice:
   `tools/test_hook_registration.py` AST-parses this file and fails it if any
   emitted string contains a skill directory name. The module docstring is
   nominally exempt, but the exemption compares against the *cleaned* docstring
   and a raw one that differs is not actually excluded -- so it is not a place to
   rely on. This paragraph is what that check felt like from the inside.
2. **Too small to frame.** A named file plus a concrete value is a change whose
   brief costs more than the work.
3. **Approach open.** Checked before the framing pass because an open-approach
   prompt usually also contains framing vocabulary. "any ideas on how we should
   approach multi-currency" names work; routing it to a brief would produce the
   anchor that stage 2 exists to avoid, so open must win the tie.
4. **A question about the current world**, rather than a request to change it.
   This sits *below* pass 3 rather than inside pass 1, and that placement is a
   fix rather than a preference: "what are our options for handling offline
   edits" opens with an interrogative and is the single clearest open-approach
   prompt in the corpus. Ordered the other way, the question form swallowed it.
5. **Work named, approach settled.**

Anything matching nothing is silent, which is the common case.

Silent when there is nothing to say, and never blocks.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# The repo's own leading gotcha: this prints `--` and em-dashes rendered from
# workflow.md, and an unconfigured cp1252 stream raises UnicodeEncodeError, which
# in a hook presents as silence rather than as an error.
if sys.platform.startswith("win"):
    for _name in ("stdout", "stderr"):
        _s = getattr(sys, _name, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".claude" / "workflow.md"

# Set to silence the classifier for one session.
OPT_OUT = "UAIOS_NO_ENTRY_CLASSIFIER"

# Same tag shape `session-start/03-state-report.py` reads, deliberately: one
# rendering convention in workflow.md rather than two.
TAG_RE = r"\[state:{key}\]\s*\n(.*?)\n\s*\[/state:{key}\]"

# A prompt shorter than this is a reply, not a request.
#
# Three, not four. "add csv export" is a framing request at three words and was
# being dropped by the floor rather than by anything about its shape -- the same
# request as "add a dark mode toggle", which passes at five. Measured against the
# corpus before lowering it: six queries sit at three words or fewer, and the
# other five are already caught by an earlier pass ("push it live" by release
# vocabulary, "is this done" and "run the linter" by matching no TASK pattern),
# so the floor was doing no work for them. A two-word prompt is still a reply.
MIN_WORDS = 3

# Above either of these, a prompt that reads as settled work is reclassified as
# open. This is the one non-vocabulary signal here, and it exists because
# vocabulary cannot carry the distinction: "build a dark mode toggle" and "build
# a platform that monitors six feeds, scores opportunities and emits roadmaps"
# are the same imperative, and only the second has an approach still to choose.
#
# The layer already states the rule this implements -- work that turns out to
# need real sequencing means the brief was too big, and the response is to go to
# stage 2 rather than to write a bigger brief. Breadth is the measurable proxy.
#
# The numbers are measured, not picked: the longest of the 180 labelled queries
# is 21 words and the median is 8, so a 28-word floor clears every existing label
# by seven words and cannot silently reclassify one. Re-measure before lowering
# it.
BREADTH_WORDS = 28
BREADTH_CLAUSES = 5

# --- pass 1: another stage owns this outright --------------------------------
#
# Each group is a stage whose own trigger vocabulary overlaps framing. Grouped by
# what they mean rather than merged, so a wrong classification is traceable to
# one line instead of to a 40-alternative regex.
HARD_STAGE = [
    # a failure, reported in any wording
    r"\bwhy (is|does|did|are|was)\b",
    r"\b(is|are|was|keeps) (broken|failing|crashing)\b",
    r"\bfail(s|ing|ed|ure)\b",
    r"\b\d{3}s\b",
    r"\b(not|isn't|doesn't) work(ing)?\b",
    r"\broot cause\b",
    r"\bstack trace\b",
    r"\bregress(ion|ed)\b",
    r"\bworked before\b",
    # ordering work that is already specified
    r"\bwrite the\b.*\bplan\b",
    r"\bbreak (this|it) down\b",
    r"\bwhat order\b",
    r"\bturn the spec into\b",
    # building
    r"\bstart building\b",
    r"\bexecute the plan\b",
    r"\bimplement (this|it|the plan)\b",
    r"\bdo task \d",
    # judging a diff
    r"\breview (this|the|my)\b",
    r"\bcheck the diff\b",
    r"\bsafe to merge\b",
    # getting it out
    r"\bdeploy\b",
    r"\brelease to\b",
    r"\bopen a pr\b",
    r"\bmerge it\b",
    r"\bpush (this|it)\b",
    r"\broll ?back\b",
    # outside evidence rather than a decision
    r"\bprior art\b",
    r"\bwhat do others do\b",
    r"\bhow do people\b",
    r"\binvestigate\b",
    # the look and feel of a user-facing surface, which has its own contract and
    # its own artefact. "what should this dashboard look like" is a surface
    # question wearing an open-approach question's grammar.
    r"\blook like\b",
    r"\blook better\b",
    r"\bdesign system\b",
    r"\bdesign (this|the) (screen|page|surface|dashboard)\b",
    r"\bcolou?r tokens?\b",
    # the agent layer itself rather than the product. These read as ordinary
    # feature work -- "add a subagent and wire it up" is framing vocabulary
    # applied to `.claude/`, and framing it as product work is the wrong stage.
    #
    # "hook" and "skill" were bare here until a review caught it, and bare was
    # wrong in the most ordinary way: they are two of the commonest words in
    # product vocabulary. "we need react hooks for the new state management" and
    # "build a skill tree for the RPG character screen" were both silently
    # swallowed by pass 1 -- settled framing work that never reached the TASK
    # pass. The 180-query corpus has no non-layer use of either word, so nothing
    # went red; it was found by probing invented prompts, which is the only way
    # an over-broad pattern ever shows up.
    #
    # They are qualified now: the word plus agent-layer context, in either order
    # and within one clause. `\bhook\b` never matched "webhook" (no word
    # boundary inside it), so that case was never affected either way.
    r"\bsub-?agent\b",
    r"\bslash command\b",
    r"\bcapability layer\b",
    r"\.claude\b",
    r"\bSKILL\.md\b",
    r"\b(post-run|pre-commit|session-start|pre-edit|pre-deploy|user-prompt)\b",
    r"\b(hook|skill)s?\b[^.]{0,40}\b(fires?|firing|triggers?|wir(e|ing)|"
    r"registered|registry|never runs|no output)\b",
    r"\b(fires?|firing|triggers?|wir(e|ing)|registered|registry)\b[^.]{0,40}"
    r"\b(hook|skill)s?\b",
]

# --- pass 4: a question about the world, not a request to change it ----------
#
# Below the open-approach pass, not merged into pass 1. See the module docstring:
# "what are our options" is both an interrogative and the corpus's clearest
# open-approach prompt, and checking the grammar first silently ate it.
INFO_QUESTION = [
    r"^what (does|do|is|are|did|was)\b",
    r"^(where|when|who)\b",
    r"^how (does|do|did|is|are)\b",
    r"^(can|does) (it|this|that|claude)\b",
]

# --- pass 2: below the floor where a brief pays for itself -------------------
TOO_SMALL = [
    # an explicit path: the change has already been located
    r"\b[\w./-]+\.(py|js|jsx|ts|tsx|md|json|ya?ml|toml|css|html|rs|go|java|rb)\b",
    r"\brename\b",
    r"\btypo\b",
    r"\bone[- ]lin(e|er)\b",
    r"\bbump (the )?version\b",
]

# --- pass 3: the approach is not settled -------------------------------------
OPEN = [
    r"\bany ideas?\b",
    r"\b(our|the|what) options\b",
    r"\boptions (are|for|here)\b",
    r"\bhow should we\b",
    r"\bbetter way\b",
    r"\b(i am|i'm|we are|we're) stuck\b",
    r"\bbrainstorm\b",
    r"\bcompare (these|the|two)\b",
    r"\bshould we build\b",
    r"\bwhich (approach|design|way|one)\b",
    r"\bhow (would|should|might) (we|you|i)\b",
    r"\bnot sure how to\b",
    r"\bopen question\b",
    r"\bapproach\b",
    r"\btrade[- ]?offs?\b",
]

# --- pass 4: work is named and the approach is settled -----------------------
TASK = [
    r"\bwe need (a way|to be able)\b",
    r"\bcan we (support|add|have)\b",
    r"\bmake it so\b",
    r"\busers? should be able\b",
    r"\bworth tracking\b",
    r"\btrack (this|that) (bug|issue)\b",
    r"\bi want (a|an|to build|to make)\b",
    r"\b(i|we) (need|want) (a|an) \w+ (app|tool|service|dashboard|page|api)\b",
    r"^(add|build|create|support|introduce)\b",
    r"\b(build|create) (a|an|the)\b",
    r"\bshould (also )?(support|handle|allow)\b",
]


def _hit(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify(prompt: str) -> str | None:
    """The state key for this prompt, or None when nothing should be said.

    Pure and dependency-free on purpose: it is the one part of this hook with a
    correctness claim, so its whole input is the string and its whole output is a
    key. `tools/test_entry_classifier.py` runs it over the labelled corpus in
    `docs/evals/trigger-queries.json` -- the same queries that define what each
    stage's description is supposed to catch, so the classifier and the
    descriptions cannot drift apart without a suite going red.
    """
    text = (prompt or "").strip().lower()
    if not text or text.startswith("/"):
        return None
    if len(text.split()) < MIN_WORDS:
        return None
    if _hit(HARD_STAGE, text):
        return None
    if _hit(TOO_SMALL, text):
        return None
    if _hit(OPEN, text):
        return "entry-open"
    if _hit(INFO_QUESTION, text):
        return None
    if _hit(TASK, text):
        # Breadth overrides the settled reading. A request naming this many
        # deliverables at once has an approach still to be chosen, whatever its
        # grammar says, and framing it would commit Goal and Outputs to the first
        # solution shape anyone wrote down.
        broad = (len(text.split()) >= BREADTH_WORDS
                 or text.count(",") >= BREADTH_CLAUSES)
        return "entry-open" if broad else "entry-unframed"
    return None


def workflow_block(key: str) -> str:
    """What `workflow.md` says about this state, or '' if it says nothing.

    No fallback text lives here, for the same reason it lives in no other hook:
    a copy would be a second source of truth about routing, and a missing tag has
    to look missing rather than be masked.
    """
    try:
        text = WORKFLOW.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = re.search(TAG_RE.format(key=re.escape(key)), text, re.S)
    return m.group(1).strip() if m else ""


def main() -> int:
    if os.environ.get(OPT_OUT):
        return 0
    payload = load_payload()
    key = classify(payload.get("prompt") or "")
    if not key:
        return 0

    block = workflow_block(key)
    if not block:
        block = (f"`.claude/workflow.md` has no `[state:{key}]` block -- add one, "
                 f"or read its Entry section for what this shape needs.")

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "entry check:\n" + block,
    }}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open. This hook only ever reports, and one that raises on a
        # malformed payload would wedge every turn.
        sys.exit(0)

---
# ═══════════════════════════════════════════════════════════════
# SKILL.md — COMPLETE SKELETON, EVERY KEY PRESENT
# Save to: .claude/skills/<name>/SKILL.md   (project — commit it)
#      or: ~/.claude/skills/<name>/SKILL.md (personal — all your projects)
#
# Every field below is a real, active key with a sensible default.
# Delete what you don't need — only `description` is recommended.
# Order doesn't matter to Claude Code; this order is by how often
# each field actually gets touched, most → least.
# ═══════════════════════════════════════════════════════════════

name: my-skill

# THE ONE LINE THAT MATTERS MOST — the only frontmatter field Claude
# reads to decide whether to auto-load the rest (there is no separate
# when_to_use field in the format). Front-load the primary trigger case,
# use the words a person would actually type, and name concrete trigger
# phrases here rather than in a second field.
description: What this skill does, then when to use it — e.g. "Summarizes uncommitted git changes and flags risks. Triggers include 'what did I change', 'review my diff', or 'write a commit message'."

argument-hint: "[filename]"

arguments: []

# true  = ONLY you can run it via /my-skill — use for anything with side
#         effects (deploy, commit, send-message); never let Claude time it.
# false = Claude can also auto-invoke it when the description matches.
disable-model-invocation: false

# false = ONLY Claude can invoke it, hidden from the / menu — use for
#         background knowledge/conventions rather than a real action.
user-invocable: true

# Tools pre-approved (no permission prompt) for the turn that invokes
# this skill. Grant clears on your next message.
allowed-tools: Read Grep Glob

# Tools removed from the pool while this skill is active. Clears on
# your next message. Use for autonomous skills that must never, say,
# stop to ask a question.
disallowed-tools: AskUserQuestion

# Model override for just this skill's turn. Leave as "inherit" unless
# you have a concrete reason:
#   haiku    -> cheap/mechanical work, don't burn session-model tokens
#   opus     -> genuinely hard reasoning and session usually runs lighter
#   sonnet   -> pin to a fixed mid-tier regardless of session model
#   inherit  -> default: same model as the conversation (recommended)
model: inherit

# Reasoning effort override, same scope as model.
# low | medium | high | xhigh | max
effort: inherit

# "fork" runs this skill in an isolated subagent instead of inline —
# the skill body becomes that subagent's task prompt. Use for anything
# that does real work (not just reference knowledge) and benefits from
# running in the background / with restricted tools.
# Leave as false for plain reference/knowledge skills.
context: false

# Which subagent type to fork into. Only read when context: fork.
# Explore | Plan | general-purpose | <custom subagent name>
agent: general-purpose

# Only read when context: fork. false = blocks your turn until the
# fork returns; true (default) = runs in the background.
background: true

# Auto-loads only when Claude is actively working with matching files.
# Leave blank/omit for a skill that should always be eligible.
paths: ""

# Which shell runs your `!`command`` injections in the body below.
# bash (default) | powershell
shell: bash

# Hooks scoped to only this skill's lifecycle (not the whole session).
# Delete this whole block if you don't need skill-scoped enforcement.
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "${CLAUDE_SKILL_DIR}/scripts/validate.sh"
---

# <Skill Title>

<!-- Pull live state into the prompt BEFORE Claude sees it. Runs once,
     at load time — preprocessing, not something Claude executes. -->
## Current context
!`git diff HEAD`

## Instructions
State the procedure as clear, imperative steps. Say what to do, not why —
this body stays in context for the rest of the session once invoked, so
every line is a recurring token cost. Keep the whole file under 500 lines.

**The heading name is yours; the ordered procedure is not optional.**
`## Three preconditions, checked in order` or `## Phase 1 — Root cause` beats
`## Instructions` when it tells the reader something, and Anthropic's published
skills use that descriptive style throughout. What is checked
(`tools/test_process_router.py`) is that a numbered or phased sequence exists at
all — two skills here had none, and no heading rule would have caught it.

1. <step one>
2. <step two>
3. <step three — what "done" looks like>

## Constraints
- <hard rule the skill must never violate>
- <edge case and how to handle it>

## Additional resources
<!-- Push detail here instead of inlining it — loads only when needed. -->
- Full reference: [reference.md](reference.md)
- Example output: [examples.md](examples.md)
- Bundled script: `${CLAUDE_SKILL_DIR}/scripts/helper.py`

<!--
  ARGUMENT SUBSTITUTION CHEAT SHEET
  $ARGUMENTS             everything passed after the skill name
  $0 / $1 / $N            positional args, shorthand for $ARGUMENTS[N]
  $name                   named arg, from the `arguments:` list above
  ${CLAUDE_SESSION_ID}    current session id
  ${CLAUDE_SKILL_DIR}     this skill's own directory
  ${CLAUDE_PROJECT_DIR}   project root
-->
---
name: context-economy-audit
model: opus
description: Audits this repo's .claude layer (skills, hooks, agents, capabilities, CLAUDE.md) and its knowledge docs for token bloat, duplicated capabilities and stale cross-references, reporting file:line findings. Use for "too many tokens", "context is filling up", "this is expensive", "sessions feel slower", "we have too many skills", "is any of this still accurate", "trim the config", to reduce token usage or context cost, to find duplicate or overlapping skills/hooks/agents, or to verify the second brain is still accurate - here "tokens" means LLM context tokens, never design tokens. Prefer this over spot-checking by hand; drift between CLAUDE.md and what is actually on disk is exactly what it detects. Do NOT use for application source code - that is no-slop-check.
context:
  - checklist.md
effort: high
argument-hint: "[scope: config | docs | both]"
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
provides: [context-audit]
requires: []
produces_artifact: false
retryable: true
---

# Context Economy Audit

Audits this repo's `.claude/` layer (skills, hooks, agents, routing,
`CLAUDE.md`), its knowledge docs (`TASK.md`/`HANDOFF.md`/`LOG.md`/etc.), or both,
per what the request actually asks for. There is no global layer to audit —
`~/.claude/` holds no skills, hooks, agents or workflows. Report-only; it never edits anything itself — fixing a
finding is a separate, explicit follow-up the user approves per finding, same
discipline as `no-slop-check`.

Distilled from a real audit, not written speculatively: every category in
[`checklist.md`](checklist.md) is a bug class this actually caught once, not a
hypothetical concern.

## Scope

Default to whatever the request implies:
- "reduce token usage" / "second brain" mentioned → the `.claude/` config layer
  (skills, hooks, agents, `routing/capabilities.md`, `CLAUDE.md`).
- The repo's docs mentioned → `TASK.md`/`HANDOFF.md`/`LOG.md`/`MEMORY.md`/
  `ISSUES.md`/`decisions/` scope.
- Ambiguous → ask which, don't guess and audit the wrong half.

Two costs are specific to this repo and worth measuring first, because both are
paid on every single turn: the `UserPromptSubmit` hook chain, and the total size
of the discoverable skill descriptions under `.claude/skills/`.

**The second one is already over budget and is the highest-value finding here.**
All 86 skills are discoverable, their descriptions total roughly 13k tokens, and
the listing is truncated — measured on 2026-07-31, about 36 skills rendered
(~5.7k tokens) and 47 arrived as bare names with no trigger surface at all.
Which half renders varies between turns, so a skill can be untriggerable on the
turn that needed it. Measure the total, and treat description length as the
lever: a shorter description that still carries its quoted trigger phrasings buys
back trigger surface for every other skill.

Note this cuts against the usual advice to add trigger phrasings — past this
budget the two goals are in direct conflict, and the audit should say so with
numbers rather than recommending both.

## Steps

1. **Read `checklist.md`** for the current categories — don't restate them from
   memory, they may have been edited since.
2. **Measure, don't estimate.** Byte/line counts come from actually running `wc -c`
   or reading the file, never guessed from a description. For hooks specifically,
   *run the hook script directly* (with a representative input) and read its real
   output — reading the source and reasoning about what it "should" produce is not
   enough; that gap is exactly how a stale doc and a regex false-positive both got
   through in the audit this checklist is based on.
3. **Cross-reference registries against reality**: `.claude/registry/*.json`
   against what is on disk, and `CLAUDE.md`'s repository map against the actual
   tree. Run `python tools/generate_registry.py` and diff — the registries are
   generated, so any difference is real drift. Also check `settings.json`'s
   `hooks` block lists every script under `.claude/hooks/*/`. Flag any entry that's missing, orphaned,
   or describes behavior the current code doesn't match.
4. **Check judgment-reliability gaps**: for any skill `CLAUDE.md` calls a default
   or "use for every X," is there an actual hook-level nudge backing it up, or does
   it rely purely on the model noticing? No hook backing isn't automatically wrong —
   just report it as a finding so it's a visible, deliberate choice, not a silent
   gap.
5. **Report**, most actionable first: fixed per-turn/per-session cost first
   (hooks firing on every turn/session are the highest-leverage fix), then
   duplication, then staleness, then judgment-reliability gaps. Each finding:
   `file:line` (or hook/skill name if no single line applies), what's wrong, and a
   one-line fix suggestion — a byte count alone isn't a finding, say why it matters.
6. **Don't fix anything automatically.** Report only; apply fixes as a separate,
   explicit step once the user approves which findings to act on.

## Relationship to other skills

- Distinct from `no-slop-check` (whole-repo dead/stale *code* sweep) and
  `code-review` (diff-scoped correctness/architecture/security) — this skill's
  subject is this repo's `.claude/` configuration layer and the knowledge-doc
  set, not application source.
- A finding that's a genuine design decision (e.g. "this skill has no hook backstop
  on purpose") belongs in that skill's own doc as a one-line rationale, not silently
  dropped — flag it to the user rather than assuming either way.

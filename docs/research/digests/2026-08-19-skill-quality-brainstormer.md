# Skill quality: brainstormer vs mloning/dotfiles's brainstorm skill

Comparable: `mloning/dotfiles`, `skills/brainstorm/SKILL.md` (public GitHub
repo; read in full via `mcp__github__get_file_contents`). Checked ECC first,
per instructions: `affaan-m/ECC` (241,033 stars) has no skill whose actual
purpose is "explore/compare solution approaches before committing" —
`council/SKILL.md` (read in full) is the closest, but it is an ambiguous
*decision* framework (four-voice adversarial verdict on an already-framed
question), not spec generation from an open problem; `blueprint`,
`santa-method`, and `intent-driven-development` (all read in full) are plan
construction, output verification, and acceptance-criteria capture
respectively — none generate/compare approaches. A GitHub code search for
`"explore approaches" OR "genuinely different" path:skills` surfaced
`mloning/dotfiles/skills/brainstorm/SKILL.md`, whose stated purpose —
"Explore approaches and capture the decision as a testable spec doc... weigh
2-3 approaches, converge, then write the spec" — is a near-exact match for
ours. Flagging honestly: this repo has 1 star (author is mloning, an sktime
co-maintainer), far below ECC's count — used because it is the closest real
topical match found, not the most popular.

## Gaps in ours (`.claude/skills/brainstormer/SKILL.md`, 238 lines)

1. **`allowed-tools` omits a `Skill`/`Task` entry for the one thing this skill
   must end with.** Line 8 is `allowed-tools: Read Grep Glob Bash` (verified —
   `Bash` **is** present, so step 7's commit is covered, and `Write` is
   deliberately absent per the skill's own line 113: "`Write` is intentionally
   not pre-approved in this layer; request the write permission... then use
   the approved command to commit it" — that is a documented design choice,
   not a bug). What the allowlist genuinely lacks is anything to dispatch step
   10's mandatory handoff to `writing-plans` — no `Skill` or `Task` entry.
   Compare `writing-plans`' own frontmatter (its line 8):
   `allowed-tools: Read Grep Glob Task Bash EnterPlanMode ExitPlanMode
   AskUserQuestion` — it grants `Task` for exactly this kind of dispatch.
   Grepping every skill's frontmatter confirms the pattern: `repo-recon`,
   `executing-plans`, `verifying-work`, `systematic-debugging`, `code-review`,
   and `research` all carry `Task` alongside their terminal handoff — of the
   skills in the chain that end by invoking another skill, `brainstormer` is
   the one outlier missing it. Fix: add `Task` to line 8.

2. **No fixed spec schema.** Step 6 (lines 106-109) says only "present the
   whole design at once" with free-form prose categories (architecture,
   components, data flow / problem, user, wedge, constraints). No requirement
   IDs, no acceptance-criteria format, no required non-goals section.
   mloning's step 6 mandates: prioritized user stories in "As an `<actor>`, I
   want `<feature>`, so that `<benefit>`" form; "testable requirements... with
   stable IDs... A requirement you can't verify is a defect"; Given/When/Then
   acceptance criteria with a concrete example ("checkout in under 3 minutes,"
   not "API < 200ms"); an explicit non-goals section. Fix: give step 6/7 a
   minimal required skeleton (IDed requirements + Given/When/Then criteria +
   non-goals) so specs are structurally comparable across runs, not just
   prose-complete.

3. **Self-review is single-agent only.** Our step 8 (lines 116-118) is the
   same agent re-reading its own spec — the exact author-bias failure mode
   `santa-method`-style skills exist to break. mloning's step 7 spawns a real
   independent second reviewer (Codex reviewing Claude's spec, or vice versa)
   with a JSON-schema-validated output contract, a hard 180s timeout via
   `perl -e 'alarm...'`, and explicit fallback prose ("second reviewer did not
   produce usable output — single-reviewer findings below") when it fails.
   Ours has no second-opinion mechanism of any kind. Fix: at minimum, spawn
   one independent reviewer subagent on the finished spec before step 9.

## Where ours is stronger

1. **State-machine-backed routing, not a prose handoff.** Our Routing section
   (lines 219-232) declares mandatory validator, terminal handoff, and
   dispatched-by/returns-to relationship inside a nine-stage workflow; the
   marker mechanism it depends on is independently enforced —
   `tools/resume.py` contains both `NEEDS CLARIFICATION` and
   `WAITING_PLAN_APPROVAL` (grepped and confirmed), so a spec with open
   markers cannot silently pass Gate 1. mloning's skill hands off to `plan`
   and mentions `research` only in prose ("follow the `research` skill... it's
   explicit-only") — no state machine holds either handoff to anything.

2. **Interruption discipline is tool-enforced, not just stated.** The
   HARD-GATE (lines 21-49) bans `AskUserQuestion` from this skill, and that
   ban is backed by the frontmatter itself: `AskUserQuestion` is absent from
   `allowed-tools` (line 8), the same tool-level enforcement pattern
   `writing-plans` uses for `ExitPlanMode`. All open questions become inline
   `[NEEDS CLARIFICATION: ...]` markers, batched into one downstream
   `AskUserQuestion` call. mloning's skill instead is fully conversational —
   step 1: "quiz me... one question at a time... restating the question
   precisely before moving on" — with no batching and nothing stopping
   additional mid-flow questions beyond a prose instruction.

3. **A self-audit apparatus mloning's skill has none of.** Our Process Flow
   dot graph (lines 158-181) makes the "no diamonds, no stops" claim visually
   checkable, and Red Flags / Common Mistakes (lines 186-210) is a named
   anti-pattern table with a "why it bites" column per entry. mloning's skill
   has no diagram and no anti-pattern catalog — a new reader has to infer
   failure modes from the numbered steps alone.

## Verdict

mloning's skill enforces artifact rigor ours lacks (a fixed, ID-based spec
schema; a real independent second reviewer with a timeout and JSON contract)
while ours enforces process rigor it lacks (state-machine-backed routing;
tool-level-blocked interruptions instead of a prose "ask one at a time")
— and ours ships one real internal gap (`allowed-tools` grants every other
skill in the chain `Task` for its terminal handoff but omits it here) that
mloning's simpler skill has no equivalent of, because it never restricts its
own tool access at all.

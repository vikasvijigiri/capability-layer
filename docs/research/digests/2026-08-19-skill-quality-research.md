# Quality comparison: `.claude/skills/research/SKILL.md` vs affaan-m/ECC `skills/deep-research/SKILL.md`

**Asked because:** judge our `research` skill against a real, comparable public
implementation and report concrete gaps in both directions.
**Verdict:** ours is the stricter evidence-discipline protocol (hard gate,
formal confidence tiers, context budgeting); ECC is the more approachable
procedural runbook (worked example, concrete tool syntax, numeric targets).
Ours should borrow ECC's worked example and source-prioritization heuristic
without loosening its evidence gates.

## Comparable found

`affaan-m/ECC`, `skills/deep-research/SKILL.md` (read in full, 2026-08-20).
Direct analog: both are "gather outside evidence, write a cited report"
skills. ECC also ships `documentation-lookup`, `iterative-retrieval`,
`market-research`, `scientific-thinking-literature-review` (not read this
pass — `deep-research` is the closest match and sufficed to answer the
question).

## Gaps in ours (concrete, with fixes)

1. **No worked example.** ECC's Step 2 shows a full example: topic "Impact
   of AI on healthcare" -> 5 concrete sub-questions, plus literal tool-call
   syntax (`firecrawl_search(query: "...", limit: 8)`). Our SKILL.md never
   shows a filled Scope block, evidence-log line, or Findings entry — only
   an abstract template with placeholders (`<question>`, `<the decision...>`).
   Fix: add one worked mini-example under Phase 1 or Phase 3 with a realistic
   question, 3 sub-questions, one evidence-log row, one Findings paragraph.

2. **No source-prioritization or search-variation heuristic.** ECC's Step 3
   gives concrete search discipline: "2-3 different keyword variations per
   sub-question," "aim for 15-30 unique sources total," and an explicit
   priority order (academic/official/reputable news > blogs > forums). Ours
   only says "at least two independent sources per sub-question" — no
   guidance on how to vary queries or rank source credibility when several
   disagree in kind (not just in claim). Fix: add a short source-quality
   ranking line to the Phase 2 table.

3. **No clarifying-question step for a standalone trigger.** ECC Step 1
   asks the user 1-2 quick questions ("learning, deciding, or writing?",
   "any specific angle?") before scoping, with a fallback to skip when the
   user says "just research it." Ours goes straight into Phase 1 Scope with
   no equivalent — fine when a caller (writing-plans, brainstormer) already
   supplies the decision context via `Asked because`, but there's no
   guidance for the case where a human triggers `research` directly with an
   underspecified ask. Fix: add an optional Step 0 clarifying-question gate
   for direct human triggers only.

4. **No self-declared drift risk for its own tool surface.** ECC opens with
   a "Drift-prone skill" banner: MCP tool names/quotas/result shapes change,
   verify configured tools before promising coverage. Ours names specific
   tools in the Phase 2 table (`mcp__github__search_code`,
   `mcp__context7__query-docs`, `WebSearch`/`WebFetch`) with no equivalent
   caveat, even though `.claude/workflow.md`'s own gotchas file documents
   that a broken/renamed tool fails silently. Fix: one line noting these
   tool names can drift and to verify availability before relying on the
   table.

## Where ours is stronger

1. **Tool-enforced hard gate vs an advisory rule.** Our `<HARD-GATE>` block
   ("NEVER synthesise from something you have not read") is paired with a
   mandatory evidence log (source/claim/confidence/sub-question) and a
   Phase-4 checklist that re-asks "is every finding traceable to a source
   you opened?" before reporting. ECC's equivalent is a single quality rule,
   "No hallucination. If you don't know, say 'insufficient data found,'" with
   no log mechanism and no pre-report check — advisory, not enforced.

2. **Formal confidence scoring vs an ad hoc flag.** Ours states an explicit
   rubric: 2+ independent sources agreeing = high, 1 source = medium,
   disagreeing sources = low (and the disagreement itself becomes a
   finding). ECC's rule 2 is "Cross-reference. If only one source says it,
   flag it as unverified" — no tiering, and the report header's
   `Confidence: [High/Medium/Low]` field has no defined criteria for how
   it's set, so two writers of the same ECC report could label it
   differently.

3. **Context-budget discipline.** Our ladder (metadata ~200 chars -> headings
   ~500 -> slice 1-3k -> whole file 5-70k, "stop at the first rung that
   answers the question") gives concrete cost figures and an explicit
   anti-pattern (its own prior research pass ingesting ~135k chars for a
   24k-char report). ECC has no token/context management guidance at all —
   it recommends "15-30 unique sources" and reading "3-5 key sources in
   full" with no cost awareness, which is a real operational risk for a
   skill that fans out across that many sources.

## Not adopted

- Did not read ECC's other four research-adjacent skills
  (`documentation-lookup`, `iterative-retrieval`, `market-research`,
  `scientific-thinking-literature-review`) — `deep-research` alone answered
  the comparison question and matched the mandate's minimum ("read in full
  at minimum").
- Did not propose adopting ECC's firecrawl/exa MCP dependency — this layer's
  `research` skill is intentionally tool-agnostic (`WebSearch`/`WebFetch` +
  `mcp__github__*` + `context7`), and pinning to two specific paid MCP
  servers would narrow rather than improve it.

## Sources

- `.claude/skills/research/SKILL.md` (this repo, read in full, 215 lines)
- `affaan-m/ECC`, `skills/deep-research/SKILL.md` (GitHub, read in full via
  `mcp__github__get_file_contents`, SHA `0f782eae59958b8464d9ecdd1e6301e45be2401b`)

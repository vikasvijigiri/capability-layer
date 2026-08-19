// ═══════════════════════════════════════════════════════════════
// Saved to: .claude/workflows/no-slop-sweep.js (project, committed)
// Runs as: /no-slop-sweep, or via `ultracode: run the no-slop-sweep workflow`
//
// Parallelizes .claude/skills/no-slop/SKILL.md's Phase 1 (sweep, read-only)
// across its own smell categories, on the "Review + merge" shape from
// guide/how_to_create_workflows.md -- per-lens analysis, one synthesis pass.
// Phase 2 (rectify) is deliberately NOT here: no-slop's own hard gate
// requires a human to see every finding before anything is repaired, and a
// workflow's spawned agents run in forced acceptEdits (docs.claude.com/
// en/workflows.md, "How a workflow runs"). Every agent() call below is
// restricted to `tools: ['Read', 'Grep', 'Glob']` (checks-runner adds
// 'Bash') -- Edit and Write are never in the list, so there is nothing for
// forced acceptEdits to auto-approve. This script only ever produces the
// report; repairs stay a human-approved Phase 2 run of the skill itself.
// ═══════════════════════════════════════════════════════════════

export const meta = {
  name: 'no-slop-sweep',
  description: 'Parallel read-only slop sweep (no-slop Phase 1 only) across its own smell categories, joined into one report',
}

// e.g. "Run /no-slop-sweep on .claude/" -> args = { scope: ".claude/" }
const scope = args?.scope ?? 'the whole repository (no-slop\'s default scope)'

const READ_ONLY = ['Read', 'Grep', 'Glob']

// ── STAGE 1: the project's own automated checks, at this scope ────────────
// no-slop's Phase 1 requires this be run FIRST and quoted, never re-derived
// by eye. Needs Bash to actually run `tools/run_checks.py --scoped`.
const checks = await agent(
  `Read .claude/skills/no-slop/SKILL.md's "Phase 1 — sweep" section, first
   paragraph only. Run the project's automated checks at scope: ${scope}
   (python tools/run_checks.py --scoped, or --tier all if --scoped does not
   apply to this scope). Quote the last relevant output line verbatim. Then
   list, in one sentence each, any smell category from that same SKILL.md
   Phase 1 that this project has NO automated check for -- the absence is
   itself a finding, per that file.`,
  {
    tools: [...READ_ONLY, 'Bash'],
    schema: {
      type: 'object',
      required: ['quoted_output', 'uncovered_categories'],
      properties: {
        quoted_output: { type: 'string' },
        uncovered_categories: { type: 'array', items: { type: 'string' } },
      },
    },
  },
)

// ── STAGE 2: fan out — one read-only agent per smell-category lens ────────
// Grouped from no-slop/SKILL.md's own Phase 1 list, not reinvented here --
// each agent is told to go read that file itself, so this script names
// categories, never criteria. A criterion restated here would be the exact
// "duplicate knowledge, paraphrased" smell the skill itself flags.
const LENSES = [
  {
    label: 'safety-correctness',
    ask: 'P0 safety and P1 correctness findings',
  },
  {
    label: 'structure-routing',
    ask: 'overlapping responsibilities, god component, orchestration leakage, and named-handoff scrutiny',
  },
  {
    label: 'consistency-provenance',
    ask: 'duplicate knowledge paraphrased, counted provenance, and dead weight',
  },
  {
    label: 'product-design',
    ask: 'P1 product quality and design-surface slop',
  },
  {
    label: 'evidence',
    ask: 'evidence slop -- claims with no artifact behind them',
  },
]

const lensReports = await pipeline(LENSES, lens =>
  agent(
    `Read .claude/skills/no-slop/SKILL.md in full first. Apply ONLY its
     Phase 1 procedure for: ${lens.ask}. Scope: ${scope}. Read-only -- you
     have no Edit or Write tool, so do not attempt any repair. Report each
     finding in that file's own format: file:line, the smell, one sentence
     on what breaks, and whether it belongs in the Local or Structural
     group per that file's own split. If this lens found nothing, say so
     explicitly and name what you read -- an empty lens is indistinguishable
     from one that never ran otherwise.`,
    {
      label: lens.label,
      tools: READ_ONLY,
      schema: {
        type: 'object',
        required: ['findings', 'read_summary'],
        properties: {
          findings: {
            type: 'array',
            items: {
              type: 'object',
              required: ['location', 'smell', 'impact', 'group'],
              properties: {
                location: { type: 'string' },
                smell: { type: 'string' },
                impact: { type: 'string' },
                group: { type: 'string', enum: ['Local', 'Structural'] },
              },
            },
          },
          read_summary: { type: 'string' },
        },
      },
    },
  ),
)

// agent() resolves to null on a stopped/unrecoverable run -- pipeline()
// keeps the null, so drop it before folding into the synthesis prompt.
const usableLensReports = lensReports.filter(Boolean)

// ── STAGE 3: synthesize — one report, no-slop's own format ────────────────
const report = await agent(
  `Read .claude/skills/no-slop/SKILL.md's "The report" section for the exact
   format. Combine these lens findings into ONE report in that format --
   file:line table, the Local/Structural split table, and the scope-covered
   statement -- exactly as that section specifies. Do not add findings; only
   combine and format. If every lens is empty, say clean and name what was
   read, per that file's own instruction.

   Automated-checks stage:
   ${JSON.stringify(checks)}

   Lens findings:
   ${JSON.stringify(usableLensReports)}

   Lenses that did not return (stopped or errored, ${LENSES.length - usableLensReports.length} of ${LENSES.length}):
   state this count in the report so a missing lens is never mistaken for
   a clean one.`,
  { tools: READ_ONLY },
)

return report

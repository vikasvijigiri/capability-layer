# Markdown writing style

Every `.md` file written or edited in this repository — skills, rules,
plans, specs, decisions, logs, docs — follows this shape. It is a standing
constraint, not a suggestion: rewrite a dense paragraph into the shapes
below rather than leaving it as prose.

- **Every section has a clear header.** No content floats without one.
- **Enumerable content is a list or a table, never a run-on paragraph.**
  Steps, options, findings, criteria, file changes — anything with more
  than one item gets one bullet or one row per item.
- **Field-shaped data is bold-label bullets, one per line** — `- **Status:**
  ...`, `- **Goal:**`, or a `| Field | Value |` table. Never comma-joined
  prose ("this is done, the goal was X, and the status is Y").
- **A labeled line stands alone at its own line start** — `**PLAN:** ...`,
  `**WHY:** ...` — not folded into a surrounding paragraph.
- **Reasoning and rationale still read as sentences**, but each point is
  its own bullet or its own short block under a sub-header, not merged
  into one undifferentiated paragraph. A decision record's `## Why` is
  argument, not a list of facts — write it as short, separated points,
  never as one dense block a reader has to re-parse to find the claim.
- **Tables for comparisons and side-by-side facts** (options weighed, a
  before/after count, a validator's rule set) — a table a reader scans
  beats the same content spelled out in prose.
- Cap prose runs at two to three sentences per bullet or block. A run
  longer than that is a sign the content wants its own sub-bullet.

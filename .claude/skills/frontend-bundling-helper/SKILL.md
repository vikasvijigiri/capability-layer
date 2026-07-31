---
name: frontend-bundling-helper
model: sonnet
description: Diagnoses and reduces client-side bundle size (code-splitting, tree-shaking, duplicate dependency detection). Use for "bundle is too big", "reduce bundle size", "why is this chunk so large", "code splitting", "tree shaking", "the app loads slowly", "the js file is huge", "why is the build so big", "first load takes ages". Prefer this over trimming code at random - duplicate dependencies usually dominate the measurement. Do NOT use for runtime performance issues unrelated to bundle size. Checks or generates against an existing design system; to define tokens, scales or DESIGN.md itself, use `design-system`.
effort: medium
---

# Bundling Helper Skill

Analyzes a production build output and recommends code-splitting/tree-shaking fixes for oversized bundles.

## When to use
- "bundle too big", "reduce bundle size", "why is this chunk so large", "code splitting", "tree shaking"

## Steps
1. Analyze `build_output_path` for chunk sizes and duplicate dependencies.
2. Identify top offenders (largest chunks, duplicated packages).
3. Recommend code-splitting points and unused-export removal.
4. Return `bundle_report` with before/after size estimates.

## Notes
Recommendations only — apply and re-measure rather than assuming the estimate for shared/critical-path code.

## Routing

**Validator (required): `.claude/validators/frontend-visual-diff.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

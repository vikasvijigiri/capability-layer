---
name: frontend-accessibility-check
model: haiku
description: Runs an automated accessibility audit (axe-core or equivalent) on a page or component and reports violations by severity. Use for "check accessibility", "a11y audit", "is this WCAG compliant", "screen reader issues", "contrast check", "can screen readers use this", "is this usable for everyone", "the contrast looks low", "accessibility audit". Prefer this over visual inspection - most violations are invisible to a sighted reviewer. Do NOT use this to auto-fix violations — it only reports. Checks or generates against an existing design system; to define tokens, scales or DESIGN.md itself, use `design-system`.
---

# Accessibility Check Skill

Runs an automated a11y ruleset against a page/component and classifies violations by severity.

## When to use
- "check accessibility", "a11y audit", "WCAG compliance", "screen reader issues", "contrast check"

## Steps
1. Run axe-core (or equivalent) in a headless runner against `url_or_component`.
2. Aggregate and classify violations by severity.
3. Return `violations_report` + remediation tips per violation.

## Notes
Report-only — does not auto-fix. Pair with `frontend-engineer` or `component-generator` to apply fixes.

## Routing

**Validator (required): `.claude/validators/frontend-visual-diff.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

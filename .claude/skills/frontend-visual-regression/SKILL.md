---
name: frontend-visual-regression
model: haiku
description: Captures and diffs screenshots of UI components/pages against a baseline to catch unintended visual changes. Use for "visual regression check", "did this change how the page looks", "screenshot diff", "did my CSS change break anything", "does it still look right", "compare it to before", "check nothing shifted". Prefer this over a manual look - small unintended shifts are exactly what the eye skips. Do NOT use for functional/behavioral testing — that's a different concern from pixel diffs. Checks or generates against an existing design system; to define tokens, scales or DESIGN.md itself, use `design-system`.
effort: low
---

# Visual Regression Skill

Captures current screenshots of `target_pages` and diffs them against `baseline_screenshots`, flagging pixel deltas above threshold.

## When to use
- "visual regression check", "screenshot diff", "did my CSS change break anything"

## Steps
1. Capture current screenshots for `target_pages` at each defined viewport.
2. Diff against `baseline_screenshots` pixel-by-pixel.
3. Flag deltas above threshold with side-by-side images.
4. Return `visual_diff_report`.

## Notes
A flagged diff isn't automatically a bug — always show the actual before/after so a human makes the intentional-vs-regression call.

## Routing

**Validator (required): `.claude/validators/frontend-visual-diff.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

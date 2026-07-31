---
name: frontend-responsive-audit
model: haiku
disallowed-tools: Edit, Write, NotebookEdit
description: Audits a page/component across breakpoints for layout breakage, overflow, and touch-target sizing. Use for "check responsiveness", "does this work on mobile", "responsive audit", "breakpoint testing", "it looks broken on my phone", "check it on mobile", "the layout breaks on small screens", "does this work on a tablet". Prefer this over resizing the browser once - overflow and touch-target problems appear at specific breakpoints. Do NOT use for accessibility-specific checks — that's accessibility-check. Checks or generates against an existing design system; to define tokens, scales or DESIGN.md itself, use `design-system`.
effort: low
---

# Responsive Audit Skill

Renders `target_page` at each of `breakpoints` and checks for overflow, layout breakage, and touch-target sizing.

## When to use
- "check responsiveness", "does this work on mobile", "responsive audit", "breakpoint testing"

## Steps
1. Render `target_page` at each breakpoint.
2. Check for horizontal overflow, clipped content, and touch-target sizes below minimum.
3. Return `responsive_report` per breakpoint with screenshots of any failures.

## Notes
Report-only — pair with `frontend-engineer` to apply layout fixes.

## Routing

**Validator (required): `.claude/validators/frontend-visual-diff.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

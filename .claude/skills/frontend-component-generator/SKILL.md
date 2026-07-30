---
name: frontend-component-generator
model: sonnet
description: Scaffolds a new UI component (markup, styles, state hooks) conforming to the project's DESIGN.md tokens. Use for "create a new component", "scaffold a button/card/modal", "add a component following our design system", "make a new component", "build the UI for this", "we need a card for this", "add a form", "put a table on this page". Prefer this over writing markup freehand - it conforms to DESIGN.md instead of inventing new spacing and colour. Do NOT use when DESIGN.md doesn't exist yet - run the design-system skill or design-engineer agent first. Checks or generates against an existing design system; to define tokens, scales or DESIGN.md itself, use `design-system`.
---

# Component Generator Skill

Scaffolds a new UI component using the project's existing design tokens (colour, spacing, typography).

## When to use
- "create a component", "scaffold a button/card/modal", "new component following our design system"

## Steps
1. Confirm `design_tokens` exist (DESIGN.md); stop and redirect if missing.
2. Generate markup + styles + minimal state using the token scale.
3. Return the component scaffold + a usage example.

## Notes
Never invents colours/spacing outside the token table — pull from DESIGN.md only.

## Routing

**Validator (required): `.claude/validators/frontend-visual-diff.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

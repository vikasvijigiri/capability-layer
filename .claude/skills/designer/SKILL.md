---
name: designer
description: Create or audit a product design contract before UI work - feeling, voice, color/type/spacing tokens, layout, components, motion, accessibility, responsive states, anti-patterns. For new screens, redesigns, design-system decisions, visual polish. Do NOT use for implementation-only coding or generic code review.
when_to_use: when a product surface needs a coherent design system or visual/UX audit
effort: high
model: sonnet
disable-model-invocation: false
---

# Designer

Create or audit the design contract before implementation. **Off-chain
capability:** enter from `task-brief`, `brainstormer`, or `writing-plans` when
the task changes a user-facing surface. Do not turn design decisions into
untracked chat context; write the contract or a dated design decision.

## Inputs and output

Read, in order:

1. The request, acceptance criteria, target users, platform, and constraints.
2. `DESIGN.md`, `design.md`, or the project's equivalent if present.
3. Existing screens and components that establish local patterns.
4. Accessibility, brand, content, and technical constraints.

Produce or update a design contract containing only decisions the product can
defend. Mark unknowns as assumptions and list the smallest blocking questions.
Do not invent a token, component variant, or interaction merely to make the
page look complete.

## Contract sections

### Product feeling and voice

- State what the product is, who it serves, and the single feeling the surface
  should produce. Prefer concrete words such as calm, fast, or trustworthy.
- Define tone, person, sentence length, allowed terminology, and examples of
  preferred and prohibited copy.
- Cover loading, empty, error, permission, success, and destructive states;
  copy is part of the design, not a placeholder.

### Tokens

- Define semantic color tokens for light and dark themes where applicable:
  surface, on-surface, primary, outline, success, warning, and danger.
- Define typography roles, font family, weights, sizes, line heights, and the
  permitted type scale.
- Define spacing, content widths, grid, gutters, breakpoints, radius, borders,
  shadows, and elevation.
- Use tokens in implementation. No one-off hex values, spacing values, or
  component exceptions without a named decision.

### Components and interaction

For every recurring component, specify variants, sizes, anatomy, states, and
when each variant is allowed. At minimum inspect buttons, links, navigation,
cards, forms, tables, dialogs, toasts, empty states, loading states, and errors.

For each interaction define:

- default, hover, focus-visible, pressed, disabled, loading, success, and error;
- keyboard order and escape behavior;
- responsive behavior and overflow handling;
- validation timing and recovery action;
- motion duration/easing, what moves, and the reduced-motion behavior.

### Accessibility floor

Treat these as release blockers unless a documented exception exists:

- WCAG AA contrast against the actual background;
- keyboard reachability and visible focus;
- semantic names for controls and meaningful icons;
- meaningful alternative text for informative images;
- no information conveyed by color alone;
- sufficient target size and readable text;
- correct heading, landmark, form-label, and error relationships;
- prefers-reduced-motion support.

## Design QA

Before handoff, compare the result against the contract at three levels:

1. **Token compliance:** no invented colors, type sizes, spacing, radii, or
   shadows.
2. **Behavioral completeness:** every important state works on narrow and wide
   layouts, with keyboard and reduced motion.
3. **Content quality:** no generic filler, emoji replacing iconography, vague
   errors, centered walls of text, or unexplained visual decoration.

When visual inspection is possible, inspect the rendered surface at representative
desktop, tablet, mobile, loading, empty, error, and keyboard-focus states. Record
the evidence and any deliberate exception with `file:line` or a screenshot path.

## Anti-patterns

Reject generic gradients, inconsistent spacing, invented colors, three unrelated
font families, unexplained cards, decorative motion, inaccessible contrast,
mobile overflow, fake empty states, and copy that hides the next action.

## Constraints

- Do not implement production code unless the user explicitly asks for it.
- Do not replace an existing design system from taste alone; propose a named
  decision and show the affected surfaces.
- Do not claim visual quality from source inspection alone when rendering is
  available; render and inspect.
- Keep the design contract concise and reusable. Move long platform-specific
  guidance into a referenced document owned by the project.

## Next step

Hand a complete contract to `brainstormer` for an open product decision,
`writing-plans` for an approved design, or `executing-plans` when the design is
already settled. If the task is implementation-only and the contract is already
complete, return to the requesting stage.

## Routing

- Enter from `task-brief`, `brainstormer`, or `writing-plans` for user-facing
  product work.
- Use `artifact-review` for an independent review of a material design contract.
- Use `no-slop` after implementation for token, state, accessibility, and
  anti-pattern checks; do not duplicate its repository-wide sweep here.

## Success

The product feeling, voice, tokens, layout, components, states, motion,
accessibility floor, anti-patterns, assumptions, and evidence are explicit;
implementation can proceed without inventing visual rules; and the next owner
is named.

---
name: designer
description: Decide a surface's visual and interaction rules, writing them into DESIGN.md. Colour tokens, typography, spacing, component states, motion and the accessibility contract. Triggers include "design this screen", "design this page", "what should this look like", "make this look better", "make it prettier", "our UI is inconsistent", "set up a design system", "define the design tokens", "pick the colors", "choose a font", "improve the UX", "this feels off". Do NOT use to build the screen (executing-plans), to sweep a finished repository (no-slop), or to choose between product approaches (brainstormer). Use this whenever work touches a user-facing surface with no design contract.
when_to_use: Trigger when the user says design this screen, design this page, what should this look like, make this look better, make it prettier, make it look professional, our UI is inconsistent, set up a design system, define the design tokens, pick the colors, choose a font, improve the UX, or this feels off.
allowed-tools: Read Grep Glob
effort: high
model: sonnet
disable-model-invocation: false
---

# Designer

Create or audit the design contract before implementation. **Off-chain
capability:** dispatched by `writing-plans`, or entered from `brainstormer`, when
the task changes a user-facing surface. Do not turn design decisions into
untracked chat context; write the contract or a dated design decision.

The output is `DESIGN.md` at the repository root, forked from
`templates/DESIGN.md` and referenced from the project's governing instructions
so it loads before any surface work. A contract that lives in a conversation is
not a contract: the next session cannot read it, and `no-slop` checks the
implemented surface against it.

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
The handoff record must name the surface and state inspected, the check applied,
the observed result, and any unresolved exception. Do not claim visual QA from
source inspection alone when rendering was available.

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

## Next step — you MUST take it

**Write the contract to `DESIGN.md`, then hand it back to the stage that entered
here** — `brainstormer` when the product decision is still open, `writing-plans`
when the design is approved and needs tasks, `executing-plans` when it was already
settled and only the rules were missing. `Write` is intentionally not
pre-approved in this layer; request the write permission before creating or
updating `DESIGN.md`. If the contract was already complete and nothing changed,
say so and return; a design pass that produces no artefact and no verdict has
produced reading, not work.

Use this compact handoff evidence shape when QA was performed:

```text
Surface/state: [what was inspected]
Check: [token, behavior, accessibility, or visual check]
Result: [observed outcome]
Exception: [none, or the deliberate exception and its evidence path]
```

## Routing

- Dispatched by `writing-plans` when the work touches a user-facing surface with
  no design contract, or entered from `brainstormer`. A dispatch returns to its
  caller; this is not a chain stage.
- For an independent review of a material contract, read
  `writing-plans/references/artifact-review.md` — it is a reference, not a skill,
  and invoking it as one is a handoff to nothing.
- Use `no-slop` after implementation for token, state, accessibility, and
  anti-pattern checks; do not duplicate its repository-wide sweep here.

## Success

The product feeling, voice, tokens, layout, components, states, motion,
accessibility floor, anti-patterns, assumptions, and evidence are explicit;
implementation can proceed without inventing visual rules; and the next owner
is named.

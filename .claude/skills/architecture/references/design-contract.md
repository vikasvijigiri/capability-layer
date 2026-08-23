# Design contract procedure

Merged from the former `designer` skill. Read this file when the spec
covers a screen, a flow, or anything a person looks at — product feeling,
voice, colour/type/spacing tokens, layout, components, motion, responsive
states, and the accessibility floor.

Create or audit the design contract before implementation. Do not turn
design decisions into untracked chat context; write the contract or a dated
design decision.

The output is `DESIGN.md` at the repository root, forked from
`templates/DESIGN.md` and referenced from the project's governing
instructions so it loads before any surface work. A contract that lives in
a conversation is not a contract: the next session cannot read it, and
`refactoring` checks the implemented surface against it.

## Inputs and output

Read, in order:

1. The request, acceptance criteria, target users, platform, and constraints.
   Identify the target platform(s) — web, iOS, Android, or more than one —
   then read the matching section(s) of `references/platform-guidance.md`
   before drafting Tokens or Components below; each platform has its own
   typography scale, navigation pattern, and motion/accessibility
   conventions that the platform-agnostic sections here do not cover.
2. `DESIGN.md`, `design.md`, or the project's equivalent if present.
3. Existing screens and components that establish local patterns.
4. Accessibility, brand, content, and technical constraints.

Produce or update a design contract containing only decisions the product
can defend. Mark unknowns as assumptions and list the smallest blocking
questions. Do not invent a token, component variant, or interaction merely
to make the page look complete.

### Ground in the source file

When the request or an existing `DESIGN.md` names a Figma file or link —
for any platform, web, iOS, or Android alike — pull the real source before
inventing a value:

- `mcp__figma__get_design_context` and `mcp__figma__get_variable_defs` for
  the actual color, type, and spacing tokens, instead of guessing hex
  values or a scale.
- `mcp__figma__get_screenshot` and `mcp__figma__get_metadata` for the
  actual layout, component tree, and states, instead of describing a
  screen from the request text alone.

Figma is the one MCP server configured in this repository that covers
every platform this contract supports — a Figma file holds an iOS or
Android app's design the same way it holds a web one, so there is no
separate per-platform MCP to choose. No linked file means there is nothing
to ground against; state that plainly and proceed from the request and
`references/platform-guidance.md` instead of treating absence as
permission to invent.

## Contract sections

### Product feeling and voice

- State what the product is, who it serves, and the single feeling the
  surface should produce. Prefer concrete words such as calm, fast, or
  trustworthy.
- Define tone, person, sentence length, allowed terminology, and examples of
  preferred and prohibited copy.
- Cover loading, empty, error, permission, success, and destructive states;
  copy is part of the design, not a placeholder.

### Tokens

- Define semantic color tokens for light and dark themes where applicable:
  surface, on-surface, primary, outline, success, warning, and danger.
- Define typography roles, font family, weights, sizes, line heights, and
  the permitted type scale.
- Define spacing, content widths, grid, gutters, breakpoints, radius,
  borders, shadows, and elevation.
- Use tokens in implementation. No one-off hex values, spacing values, or
  component exceptions without a named decision.

### Components and interaction

For every recurring component, specify variants, sizes, anatomy, states,
and when each variant is allowed. At minimum inspect buttons, links,
navigation, cards, forms, tables, dialogs, toasts, empty states, loading
states, and errors.

For each interaction define:

- default, hover, focus-visible, pressed, disabled, loading, success, and
  error;
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
2. **Behavioral completeness:** every important state works on narrow and
   wide layouts, with keyboard and reduced motion.
3. **Content quality:** no generic filler, emoji replacing iconography,
   vague errors, centered walls of text, or unexplained visual decoration.

When visual inspection is possible, inspect the rendered surface at
representative desktop, tablet, mobile, loading, empty, error, and
keyboard-focus states. Record the evidence and any deliberate exception
with `file:line` or a screenshot path. The handoff record must name the
surface and state inspected, the check applied, the observed result, and
any unresolved exception. Do not claim visual QA from source inspection
alone when rendering was available.

## Anti-patterns

Reject generic gradients, inconsistent spacing, invented colors, three
unrelated font families, unexplained cards, decorative motion, inaccessible
contrast, mobile overflow, fake empty states, and copy that hides the next
action.

## Constraints

- Do not implement production code unless the user explicitly asks for it.
- Do not replace an existing design system from taste alone; propose a
  named decision and show the affected surfaces.
- Do not claim visual quality from source inspection alone when rendering
  is available; render and inspect.
- Keep the design contract concise and reusable. Move long
  platform-specific guidance into a referenced document owned by the
  project.

## Handoff

Write the contract to `DESIGN.md`, then hand it back to the stage that
entered this procedure — `architecture`'s own options-comparison procedure
when the product decision is still open, `task-analysis` when the design is
approved and needs tasks, `implementation` when it was already settled and
only the rules were missing. `Write` is intentionally not pre-approved in
this layer; request the write permission before creating or updating
`DESIGN.md`. If the contract was already complete and nothing changed, say
so and return; a design pass that produces no artefact and no verdict has
produced reading, not work.

Use this compact handoff evidence shape when QA was performed:

```text
Surface/state: [what was inspected]
Check: [token, behavior, accessibility, or visual check]
Result: [observed outcome]
Exception: [none, or the deliberate exception and its evidence path]
```

Use `refactoring` after implementation for token, state, accessibility, and
anti-pattern checks; do not duplicate its repository-wide sweep here.

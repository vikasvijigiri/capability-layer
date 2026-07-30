---
name: design-system
model: opus
description: Owns a project's DESIGN.md — design tokens, type and spacing scales, status colour semantics, accessibility rules — forking the global template into the repo the first time UI work appears, and otherwise checking generated output against its token table, layout scale and anti-pattern list. Use whenever the work touches UI, UX, styling, layout, theming, components, CSS or a design system, and always before writing the first component in a project with no DESIGN.md. Also triggered by vague visual asks - "make it look better", "it looks off", "pick a colour for this", "what font should we use", "make it feel more polished", "the spacing looks wrong", "match our brand". Prefer this over inventing colours, spacing or breakpoints inline. Do NOT use for backend or non-visual work.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
---

# Design System

A project's design system lives in its own repo-root `DESIGN.md` — not
here. This skill's job is narrow: get that file to exist (forked from
[`DESIGN.template.md`](DESIGN.template.md)) the first time it's actually
needed, wire the one-line reference into `CLAUDE.md`, and use it as the
check against generated UI output. It does not own the rest of a
project's `CLAUDE.md` — that's `repo-onboarding`.

## If the project has no `DESIGN.md` yet

Only do this once real UI/UX/frontend work is actually being asked for —
not reflexively, and not for a project that's never going to have a UI
(don't fork a design system into a CLI tool or a data pipeline).

1. Copy [`DESIGN.template.md`](DESIGN.template.md) to the project's root
   as `DESIGN.md`.
2. Fill in what you can *actually* infer from the request/conversation —
   don't invent specifics that weren't given (colors, fonts, spacing
   scale). Leave placeholders as placeholders rather than guessing real
   values; a wrong guessed value is worse than an honest blank, since it
   looks authoritative and won't get questioned.
3. Add a **Design** section to the project's `CLAUDE.md` (create the file
   via `repo-onboarding` first if it doesn't exist):
   ```
   ## Design

   For any UI/UX or frontend help, read [`DESIGN.md`](DESIGN.md) first.
   ```
4. Tell the user directly that the template needs their input on the
   sections you couldn't fill in (voice, real color values, type scale)
   — don't silently ship a half-filled spec as if it were complete.

## If the project already has a `DESIGN.md`

Read it before any surface-level work (new component, page, styling
change) — it's the source of truth, not this skill's own judgment.

- Never invent a color outside the token table.
- Never introduce a spacing/sizing value off the declared scale.
- Check generated output against the anti-pattern list before calling
  the work done.
- Respect the accessibility floor as non-negotiable, not aspirational.
- If something you need isn't covered by the existing spec, say so and
  ask, or propose an addition — don't quietly improvise and leave the
  spec stale relative to what actually shipped.

## Relationship to other skills

- `repo-onboarding` owns the rest of `CLAUDE.md` (what the project is,
  architecture, commands) — this skill only owns the one Design section
  pointing at `DESIGN.md`.
- `engineering-policy`'s context-economy principle applies here too:
  don't re-read `DESIGN.md` every single turn once it's already loaded —
  read it when starting UI work, not on every message.
- `frontend-ux-flow` runs *before* this skill on a new feature — which screens
  exist is not a token decision. This skill then gates
  `frontend-component-generator` and `frontend-form-builder`, which may not run
  until `DESIGN.md` exists.

## Importing tokens from Figma

When the project has a Figma file, derive `DESIGN.md` from it rather than
inventing a parallel scale — two sources of truth for colour and spacing always
drift, and the design file wins the argument later anyway.

The Figma MCP server is wired in `.mcp.json`. Use it in this order:

1. `mcp__figma__get_variable_defs` — the actual token definitions (colour,
   spacing, typography variables). This is the authoritative source; prefer it
   over reading values off a screenshot.
2. `mcp__figma__get_design_context` — component structure and layout rules for
   the frame being implemented.
3. `mcp__figma__get_screenshot` — visual reference only, for checking the built
   result against intent.
4. `mcp__figma__get_code_connect_map` — if the file already maps components to
   code, honour those mappings instead of scaffolding new components.

Transcribe the imported values into `DESIGN.md` as the repo's own token table.
`DESIGN.md` stays canonical for code; Figma stays canonical for design. Record
the Figma file URL in `DESIGN.md` so the provenance is traceable, and re-import
rather than hand-patching when the design file changes.

Per the Figma MCP server's own instructions, load the `/figma-use` skill before
calling `mcp__figma__use_figma` — that tool writes into Figma, and pushing
generated design back is a side effect that needs the same approval as any
other outward-facing change.

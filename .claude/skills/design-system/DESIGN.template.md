# DESIGN.md — [Project Name]

> Fork this. Fill every section. Reference it from `CLAUDE.md` so the
> agent reads it before any surface-level work. Delete this blockquote
> when you fork.

## What this is

_(One paragraph: what the product is, who it's for, and the single
feeling the design should produce. Be concrete — "calm, fast,
trustworthy" beats "modern and clean.")_

## Voice

- Tone: _[e.g. direct, warm, no hype — short sentences]_
- Person: _[first person? second? "we" or "you"?]_
- Do: _[say "Couldn't save — check your connection"]_
- Don't: _[say "Oops! Something went wrong"]_
- Reference: _[a product whose voice you'd want to be mistaken for]_

## Color tokens

Define tokens, not one-off hex values. The agent should never invent a color.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--surface` | | | Page background |
| `--on-surface` | | | Primary text |
| `--primary` | | | Accent, CTAs |
| `--outline` | | | Borders, dividers |

Rule: no token, no new color without discussion.

## Type

- Display / headings: _[font, weights, when to use]_
- Body: _[font, size, line-height]_
- Mono: _[font, where it's allowed]_
- Scale: _[the actual sizes — don't let the agent pick]_

## Layout & spacing

- Spacing scale: _[e.g. 4 / 8 / 16 / 24 / 32 / 64 — and nothing in between]_
- Max content width: _[e.g. 720px prose, 1180px app]_
- Grid: _[columns, gutters, breakpoints]_
- Radius / elevation: _[the allowed values]_

## Components

- Buttons: _[variants, sizes, when each is used, what's never allowed]_
- Cards: _[padding, border, hover behavior]_
- Forms: _[label position, error display, validation timing]_
- Empty states: _[must have: ...]_

## Motion

- Default transition: _[duration, easing]_
- What animates: _[and what must not]_
- Reduced-motion: _[the rule]_

## Accessibility floor

Non-negotiable minimums:
- Contrast meets WCAG AA against its actual background
- Every interactive element is keyboard-reachable and has a visible focus state
- Images have meaningful alt; icons that carry meaning have labels
- Nothing conveys information by color alone
- Respects `prefers-reduced-motion`

## Anti-patterns — never ship these

- Generic AI gradient-on-everything aesthetic
- Inconsistent spacing (values off the scale)
- Invented colors not in the token table
- Emoji in place of real iconography or real copy
- Centered walls of text
- Three font families where one would do
- _[your project's specific ones]_

**How to use**: check generated output against the token table, layout
scale, and anti-pattern list. If something is not covered, fill the spec
before delegating.

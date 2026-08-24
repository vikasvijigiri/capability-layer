# DESIGN.md — [Project Name]

<!-- Fork this to the repository root. Fill every section. Reference it from
CLAUDE.md so it loads before any surface work. Delete this comment when you fork.

An unfilled section is worse than an absent one: the agent reads `[e.g. direct,
warm]` as the decision and ships it. If you do not know yet, write
`[NEEDS DECISION: ...]` — `architecture` treats that as a blocking question, and a
placeholder as an answer. -->

## What this is

One paragraph: what the product is, who it is for, and the single feeling the
design should produce. Be concrete — "calm, fast, trustworthy" beats "modern and
clean", because the second one cannot be checked against anything.

**Platform:** [web / iOS / Android / more than one — see
`.claude/skills/architecture/references/platform-guidance.md` for the
platform-specific guidance this contract draws on]

## Voice

How the product talks — UI copy, errors, empty states, docs.

- **Tone:** [e.g. direct, warm, no hype — short sentences]
- **Person:** [first, second? "we" or "you"?]
- **Do:** [say "Couldn't save — check your connection"]
- **Don't:** [say "Oops! Something went wrong 😅"]
- **Reference:** [a product whose voice you would want to be mistaken for]

Copy covers loading, empty, error, permission-denied, success and destructive
states. Placeholder copy is an unfinished design, not a detail for later.

## Color tokens

Tokens, never one-off hex values. The agent must never invent a color.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--surface` | `#______` | `#______` | Page background |
| `--on-surface` | `#______` | `#______` | Primary text |
| `--primary` | `#______` | `#______` | Accent, CTAs |
| `--outline` | `#______` | `#______` | Borders, dividers |
| `--success` | `#______` | `#______` | Confirmation |
| `--warning` | `#______` | `#______` | Caution |
| `--danger` | `#______` | `#______` | Destructive, errors |

**Rule: no token, no new color without a named decision.**

## Type

- **Display / headings:** [font, weights, when each is used]
- **Body:** [font, size, line-height]
- **Mono:** [font, and where it is allowed]
- **Scale:** [the actual sizes — do not let the agent pick]

## Layout and spacing

- **Spacing scale:** [e.g. 4 / 8 / 16 / 24 / 32 / 64 — and nothing between]
- **Max content width:** [e.g. 720px prose, 1180px app]
- **Grid:** [columns, gutters, breakpoints]
- **Radius / elevation:** [the allowed values]

## Components

For each recurring component, the rules the agent must follow. Add as you go.

- **Buttons:** [variants, sizes, when each is used, what is never allowed]
- **Cards:** [padding, border, hover behaviour]
- **Forms:** [label position, error display, validation timing]
- **Empty states:** [what one must always contain]

## Motion

- **Default transition:** [duration, easing]
- **What animates:** [and what must not]
- **Reduced motion:** [the rule]

## Accessibility floor

Non-negotiable minimums. Treat a miss as release-blocking unless a documented
exception names the rule, the reason, the owner, and the expiry.

- [ ] Contrast meets WCAG AA against its **actual** background
- [ ] Every interactive element is keyboard-reachable with a visible focus state
- [ ] Images have meaningful alt; icons carrying meaning have labels
- [ ] Nothing conveys information by colour alone
- [ ] Respects `prefers-reduced-motion`

## Anti-patterns — never ship these

The slop list, design edition. Output is checked against it.

- [ ] Generic AI gradient-on-everything aesthetic
- [ ] Spacing off the scale
- [ ] Colours not in the token table
- [ ] Emoji standing in for real iconography or real copy
- [ ] Centred walls of text
- [ ] Three font families where one would do
- [ ] [your project's specific ones]

---

**How to use:** check generated output against the token table, the layout scale
and the anti-pattern list. If something is not covered, fill the spec before
delegating — an agent given an unanswered question answers it silently.

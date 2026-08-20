# Skill quality: designer vs affaan-m/ECC design skills

Comparable: `affaan-m/ECC` (public GitHub repo), `skills/design-system/SKILL.md`
(closest match — it is the only ECC skill that writes a `DESIGN.md` contract to
disk; also read `skills/frontend-design-direction/SKILL.md` as a secondary
comparable — it applies design judgment inline and writes no artifact at all,
confirming `design-system` is the fairer match for "produce a durable
contract"). Both read in full via `mcp__github__get_file_contents`.

## Gaps in ours (`.claude/skills/designer/SKILL.md`, 142 lines)

1. **No machine-readable or renderable output, only prose.** ECC's Mode 1
   emits `DESIGN.md` **+** `design-tokens.json` **+** an interactive
   `design-preview.html`. Ours emits `DESIGN.md` alone — nothing a linter or a
   build step can consume, nothing a reviewer can open and see rendered.
   Fix: add a `design-tokens.json` (or CSS custom-properties file) as a
   required companion artifact alongside `DESIGN.md`.

2. **No quantified audit.** ECC's Mode 2 scores the UI 0–10 across 10 named
   dimensions (color consistency, typography hierarchy, spacing rhythm, dark
   mode, accessibility, polish, etc.) with a fix at `file:line` per dimension.
   Our "Design QA" section (lines 86–99) is a 3-bucket qualitative checklist
   with no scoring mechanism, so two designers reviewing the same surface
   have no comparable output. Fix: convert the three QA buckets into scored
   dimensions.

3. **No competitor/external-reference step.** ECC's generator explicitly
   scans 3 competitor sites via browser MCP as step 3 of its process. Our
   "Inputs" list (lines 25–30) only reads the request, existing `DESIGN.md`,
   local screens, and constraints — no external grounding step at all, so a
   design decision can be made purely from internal precedent even when none
   exists.

4. **Zero worked examples.** ECC shows literal invocation examples
   (`/design-system generate --style minimal --palette earth-tones`,
   `/design-system audit --url http://localhost:3000 --pages / /pricing
   /docs`). Ours describes what each section must contain but never shows a
   filled example of a token block, a component state table, or a QA verdict
   — a new user has to infer the shape from the prescription alone.

## Where ours is stronger

1. **Accessibility is a release blocker, not a scoring line.** Ours (lines
   73–84) lists eight concrete, enforceable criteria — WCAG AA contrast,
   focus-visible, semantic control names, alt text, no color-only meaning,
   target size, heading/landmark/label relationships, `prefers-reduced-motion`
   — and frames them as gates. ECC's only accessibility mention is one
   scoring line, "Accessibility — contrast ratios, focus states, touch
   targets," with no reduced-motion or landmark/label coverage at all.

2. **Full interaction-state contract per component.** Ours (lines 65–71)
   requires default/hover/focus-visible/pressed/disabled/loading/success/error
   plus keyboard order, escape behavior, validation timing, and motion
   duration/easing with reduced-motion fallback, for every recurring
   component. Neither ECC skill enumerates component states at all —
   `frontend-design-direction` only says "use motion sparingly."

3. **Wired into a chain of custody, not a standalone tool.** Ours is
   dispatched by `writing-plans`/`brainstormer`, is read-only
   (`allowed-tools: Read Grep Glob`) so it cannot slide into implementation,
   and has an explicit "Next step you MUST take" that names the returning
   owner. ECC's `frontend-design-direction` explicitly blends design and
   build ("Build the actual usable experience as the first screen"), and
   neither ECC skill hands off to, or is gated by, anything else in that repo.

## Verdict

Ours enforces the contract (accessibility, states, chain-of-custody) more
rigorously than ECC does; ECC produces a more *usable* artifact (JSON tokens,
rendered preview, scored audit, worked commands) — the fix is to keep our
gates and adopt ECC's machine-readable output and scoring mechanism.

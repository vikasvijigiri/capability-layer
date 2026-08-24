# Should this repo add new skill(s) for web and Android/iOS UI/UX design, and what MCP should they use?

**Asked because:** the user asked for a "world-class" UI/UX skill for web app and Android/iOS
app design, wired to the "respective" design MCP(s), feeding a `task-analysis` plan for
`capability-layer-maintenance` to execute.

**Verdict:** Do not create new top-level skill(s). This repo already owns the equivalent
capability — `architecture`'s design-contract mode (`references/design-contract.md`,
merged from the former `designer` skill), which writes `DESIGN.md` for "a screen, a flow, or
anything a person looks at." It is currently written web-first (WCAG, keyboard, CSS
breakpoints) with no iOS/Android platform guidance and no MCP wiring. The gap is real but
narrow: add platform-specific reference files (web / iOS / Android) under
`architecture/references/`, and wire Figma MCP into the skill's `allowed-tools` plus a
usage rule — Figma is the only MCP in this ecosystem that actually covers all three
platforms; no working Xcode/Android-Studio design MCP exists in current public prior art.

## Findings

### (a) What do real, publicly-read Claude Code UI/UX skills contain?

**Finding 1 — the "hub + platform modules" shape is the dominant pattern for
platform-specific design guidance.** `rshankras/claude-code-apple-skills`
(`skills/ios/SKILL.md`, read in full via `get_file_contents`) is a thin router: its
frontmatter description names the trigger cases, and its body is a table of
subdirectories (`ui-review/`, `accessibility-audit/`, `navigation-patterns/`, ...), each
its own `SKILL.md`, read on demand ("Read relevant module files based on the user's
needs"). `ui-review/` is explicitly "UI/UX review against Apple HIG." Confidence: **high**
(primary source, matches this repo's own already-adopted convention of pushing depth into
`<skill>/references/*.md` loaded per task rather than per turn — see
`architecture/references/design-contract.md`).
**Means here:** platform depth belongs in reference files under the existing
`architecture` skill, not new top-level skills — this repo already uses the pattern the
best prior art also converges on.

**Finding 2 — the strongest real skill in this space handles Web, Android (Compose), and
Apple (SwiftUI) from *one* skill via stack detection, not three siloed skills.**
`AThevon/genjutsu`'s `skills/cast/SKILL.md` (read in full) opens with a `SCAN` phase that
greps `package.json`, Gradle files, and `Package.swift`/`.xcodeproj` to detect the actual
stack, then loads only the matching platform sub-skill
(`mobile-principles`, `compose-motion`, `swiftui-motion`, ...). Its `AUDIT` phase has a
platform-specific checklist (Web: contrast, AnimatePresence, 60fps; Compose: recomposition
counts, `Modifier.semantics`; SwiftUI: Reduce Motion, Dynamic Type 200%). It also states
"Iron Rules" rejecting "generic/AI slop... rainbow gradients, gratuitous glassmorphism,
'modern and sleek.'" Confidence: **high** (primary source, real production skill with
30k+ chars of engineered procedure).
**Means here:** the existing `design-contract.md` already independently converged on the
same anti-slop stance ("Anti-patterns" section: "generic gradients... invented colors...
decorative motion"). Confirms current content is not behind. What it lacks that `cast`
has: no platform-detection step and no platform-specific audit checklist — exactly what a
new reference file should add.

**Finding 3 — a data-heavy "design intelligence" skill exists but solves a different
problem (asset generation, not a design contract).** `nextlevelbuilder/ui-ux-pro-max-skill`
ships `ui-ux-pro-max` (searchable local datasets: 79 styles, 192 palettes, 74 font
pairings, 119 UX guidelines) plus sibling skills `design-system` (token architecture),
`ui-styling` (shadcn/Tailwind), `banner-design`, `brand`. Confidence: **medium**
(frontmatter and file tree read via `search_code`/`get_file_contents`; full skill bodies
not read — the frontmatter alone was sufficient to answer the "does it exist and what
does it cover" question).
**Means here:** out of scope to imitate directly — it is a generation tool for marketing
assets/logos, not a design-contract-and-gate skill. Its "token architecture" framing
(primitive→semantic→component) is already present in `design-contract.md`'s "Tokens"
section in equivalent form.

**Finding 4 — this repo already ran this exact comparison once, in-repo, and reached a
compatible verdict.** `docs/research/digests/2026-08-19-skill-quality-designer.md` (an
in-repo digest, opened directly, not re-fetched) compared the former `designer` skill
against `affaan-m/ECC`'s `design-system` skill and found ours **stronger** on
accessibility-as-gate and full interaction-state contracts, **weaker** on machine-readable
output (`design-tokens.json`), quantified scoring, and external/competitor grounding.
Confidence: **high** (primary source, already in the repository).
**Means here:** the gap this session was asked to close (platform coverage + MCP wiring)
is a different, narrower gap than the one already found and not yet fixed
(`design-tokens.json`, scored QA, competitor grounding). Both are legitimate `Extend`
targets for the same file; only the platform/MCP gap is in scope for this task.

### (b) What MCP servers exist for web and mobile (iOS/Android) design workflows?

**Finding 5 — Figma is the only MCP server actually used for design grounding in any
source opened this session, for any of the three platforms.** Neither
`claude-code-apple-skills` (iOS) nor `genjutsu` (Web/Android/iOS) references an MCP server
at all for design; `genjutsu`'s SCAN phase uses only `Bash`+`grep`, and its `allowed-tools`
frontmatter lists `Bash, Read, Edit, Write, Grep, Glob, WebSearch, Artifact` — no MCP.
WebSearch for "Claude Code MCP for iOS Android app design SwiftUI Material Design 2026"
returned only skill listings (iOS Mobile Design, iOS Design System Architect,
mobile-ios-design), never an MCP server. Confidence: **high** for "no verified
Xcode/Android-Studio design MCP was found"; this is an absence claim from a bounded
search, not exhaustive proof none exists anywhere.
**Means here:** this repo's `.mcp.json` already has `figma` (`https://mcp.figma.com/mcp`,
already used elsewhere per its instructions block: `get_design_context`, `get_screenshot`,
`get_variable_defs`, `get_code_connect_map`, `get_metadata`) and nothing else
design-specific. Figma is legitimately "the respective MCP" for **both** web and mobile —
Figma files hold iOS and Android app designs the same way they hold web ones — so one MCP
wiring, not three, covers the ask. `architecture/SKILL.md`'s current `allowed-tools: Read
Grep Glob Bash` does not include any Figma MCP tool, so even though Figma is configured
repo-wide, the skill that would use it cannot call it today. That is the actual wiring
gap, not a missing MCP server.

### (c) Does Anthropic publish an official UI/UX or frontend-design skill?

**Finding 6 — no official Anthropic UI/UX skill was found in
`anthropics/claude-plugins-official`.** A repo search scoped to `org:anthropics
topic:skills` returned exactly one repository, `claude-plugins-official`, described as "a
directory of high quality Claude Code Plugins" rather than a skill source itself; its
internal skill contents were not enumerated this pass (out of scope — the directory-of-
plugins framing means any UI/UX plugin inside it is third-party, not Anthropic-authored,
and would need the same evaluation as the other prior art above). Confidence: **medium**
(one search, not a full crawl of the directory's contents).
**Means here:** no official Anthropic reference to mirror; the community prior art above
(`claude-code-apple-skills`, `genjutsu`) is the best available signal.

## Disagreements

None of the sources conflict on structure (hub+modules, or single-skill-with-stack-
detection are both legitimate and not contradictory — they answer different questions:
"is the depth organized by platform" vs. "is the platform chosen automatically"). No
source claimed an MCP server exists for Xcode/Android Studio design work; this is
agreement by absence, not a resolved disagreement.

## Not adopted

- **A brand-new top-level `web-ui-ux` / `mobile-ui-ux` skill pair.** Rejected: it would
  duplicate `architecture`'s existing HARD-GATE (no code, no `AskUserQuestion`, markers
  only), its Gate 1 handoff to `task-analysis`, and its `DESIGN.md` output contract —
  exactly the "Never: create a duplicate implementation of something that already exists"
  rule in `CLAUDE.md`. `design-contract.md`'s own text already says "Move long
  platform-specific guidance into a referenced document owned by the project" — the
  extension point already exists and names itself.
- **`nextlevelbuilder/ui-ux-pro-max-skill`'s searchable-dataset approach** (79 styles, 192
  palettes as literal data files) — a heavier mechanism than this task needs; the gap
  identified is platform *guidance* (Material Design 3 vs. HIG vs. web conventions) and
  MCP wiring, not a style/palette generator.
- **Building a bespoke MCP bridge for Xcode or Android Studio.** No public prior art
  showed one working; scope creep relative to what was asked (research existing MCPs, not
  build a new one).

## Sources

- `rshankras/claude-code-apple-skills`, `skills/ios/SKILL.md` — read in full via
  `mcp__github__get_file_contents`.
- `AThevon/genjutsu`, `skills/cast/SKILL.md` — read in full via
  `mcp__github__get_file_contents`.
- `nextlevelbuilder/ui-ux-pro-max-skill` — frontmatter/description of `design/SKILL.md`,
  `ui-ux-pro-max/SKILL.md`, `design-system/SKILL.md`, `ui-styling/SKILL.md`,
  `banner-design/SKILL.md`, `brand/SKILL.md`, `slides/SKILL.md` via
  `mcp__github__search_code`.
- This repository: `.claude/skills/architecture/SKILL.md`,
  `.claude/skills/architecture/references/design-contract.md`,
  `docs/research/digests/2026-08-19-skill-quality-designer.md`,
  `.mcp.json` — read directly.
- `mcp__github__search_repositories` for `org:anthropics topic:skills` — one hit,
  `anthropics/claude-plugins-official`, not further crawled.
- `WebSearch`: "Claude Code MCP for iOS Android app design SwiftUI Material Design 2026" —
  result titles only (mcpmarket.com, claudedirectory.org, dev.to, mcp.directory listings),
  none opened in full; used only to corroborate the absence finding in (b), not as a
  standalone claim source.

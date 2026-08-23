# UI/UX design (web + iOS/Android) MCP wiring — Implementation Plan

**Goal:** Give `architecture`'s existing design-contract mode (the skill that already
writes `DESIGN.md` for "a screen, a flow, or anything a person looks at") real iOS and
Android platform guidance and a working wire into the Figma MCP server, instead of
creating new, duplicate top-level skills.

**Source brief:** this session's framing, grounded by
`docs/research/2026-08-23-ui-ux-skill-prior-art.md`

**Slug:** ui-ux-design-mcp-skill

**Risk:** **low** — computed: `python tools/scope.py --plan
docs/plans/2026-08-23-ui-ux-design-mcp-skill.md` reports "risk: low -- no clause forces a
tier above low" and "scope: small -- none of 5 clauses fired" (9 declared paths; none is a
migration, lockfile, CI config, hook, agent, `workflow.md`, `settings.json`, auth,
credential, installer, or packaging file). Corrected from this plan's own provisional
`high` guess at Gate 1 — the portability contract and adapter manifests are not on
`scope.py`'s veto list, and the computed verdict overrides the guess. Not a request to
skip Gate 2 either way.

**Blast radius:** `.claude/skills/architecture/` (SKILL.md + references/), a new
`.claude/rules/` file, the host-neutral capability contract
(`.claude/portability/capabilities.json`) and all three adapter manifests
(`.claude/adapters/*.json`), and `templates/DESIGN.md`. No application code — this repo
ships none. No hook, no lifecycle stage, no new skill.

**Rollback:** every change is additive text in tracked files; `git revert`/`git checkout --
<path>` on any subset cleanly restores prior behavior. No migration, no data, no
irreversible step.

**Architecture:** Research (`docs/research/2026-08-23-ui-ux-skill-prior-art.md`) found (a)
this repo already owns the equivalent capability — `architecture`'s design-contract mode,
merged from the former `designer` skill, which explicitly says "move long
platform-specific guidance into a referenced document owned by the project"; (b) the
strongest public prior art (`AThevon/genjutsu`'s `cast` skill) handles Web, Android, and
Apple from one skill via stack/platform detection, not three siloed skills, and neither it
nor `rshankras/claude-code-apple-skills` wires any MCP server for design at all; (c) this
repo's `.mcp.json` already configures Figma, the only MCP in any source opened that
actually covers all three platforms (a Figma file holds iOS/Android/web designs alike). So:
**extend, don't duplicate** — add a platform-guidance reference file, wire Figma MCP tool
names into `architecture`'s `allowed-tools`, and register those tool names through the
*existing* host-neutral capability contract, reusing the `web_research` capability bucket
`mcp__github__search_code`/`mcp__context7__query-docs` already use (inventing a new
capability category would require editing `tools/test_portability_contract.py`'s hardcoded
capability-name set — a heavier, riskier change with no benefit here).

**Tech stack and constraints:** No application code exists in this repo (per `CLAUDE.md`).
Pure `.claude/` + `templates/` contract edits. Must not touch `.claude/workflow.md`'s stage
table — `architecture` stays the sole Design-stage owner, no new lifecycle stage. Must not
pre-approve `Write`/`Edit`/`NotebookEdit` in any skill's `allowed-tools`
(`test_process_router.py` enforces this). Every new `source_term_capabilities` entry must
appear literally inside some `SKILL.md` file, not only in a `references/` file
(`test_portability_contract.py`'s `used_terms == set(term_capabilities)` check scans only
files literally named `SKILL.md`). The new rule must state a standing constraint, not a
procedure (`templates/rules.md`'s own decision test), and must be path-scoped
(`paths:`) rather than global, per that template's own guardrail against unscoped rules.

## File map

| Path | Action | Owns |
|---|---|---|
| `.claude/skills/architecture/references/platform-guidance.md` | Create | iOS (Apple HIG) and Android (Material Design 3) platform sections; points back to the base contract for web, which is already web-shaped |
| `.claude/skills/architecture/references/design-contract.md` | Modify | add a "Platform" input step + cross-link (Task 1); add a "Ground in the source file" Figma MCP subsection (Task 2) |
| `.claude/skills/architecture/SKILL.md` | Modify | add 4 Figma MCP tool names to `allowed-tools` |
| `.claude/portability/capabilities.json` | Modify | register the 4 new tool names under `source_term_capabilities`, mapped to the existing `web_research` capability |
| `.claude/adapters/claude-code.json` | Modify | resolve the 4 new terms as `host-configured` |
| `.claude/adapters/codex.json` | Modify | resolve the 4 new terms as `host-managed` |
| `.claude/adapters/generic-agent.json` | Modify | resolve the 4 new terms as `host-managed` |
| `.claude/rules/design-mcp.md` | Create | path-scoped standing rule: ground design work in Figma MCP when a Figma file is linked; Figma is the one MCP that covers web/iOS/Android here |
| `templates/DESIGN.md` | Modify | fix the stale `designer` skill reference (merged into `architecture` on 2026-08-21) and add a "Platform" line |

## Progress

- [x] Task 1 — Add iOS/Android platform guidance, cross-linked from the design contract
- [x] Task 2 — Wire Figma MCP into `architecture`'s tools and grounding procedure
- [x] Task 3 — Register the new MCP tool terms in the portability contract and all adapters
- [x] Task 4 — Add the path-scoped design-MCP rule
- [ ] Task 5 — Fix `templates/DESIGN.md`'s stale skill reference and add a Platform line

## Tasks

### Task 1: Add iOS/Android platform guidance, cross-linked from the design contract
**Purpose:** close the platform gap `docs/research/2026-08-23-ui-ux-skill-prior-art.md`
found — the existing design contract is web-shaped (WCAG, keyboard, CSS breakpoints) with
no iOS/Android guidance, even though it already invites exactly this extension
("move long platform-specific guidance into a referenced document").
**Files:**
- Create: `.claude/skills/architecture/references/platform-guidance.md` — three headed
  sections: Web (one line pointing back to `design-contract.md`, which already covers it),
  iOS (Apple HIG: SF Symbols, Dynamic Type, safe areas, NavigationStack/TabView patterns,
  Reduce Motion, VoiceOver), Android (Material Design 3: dynamic color, elevation tokens,
  Compose motion scheme, TalkBack, touch target minimums, edge-to-edge/gesture nav)
- Modify: `.claude/skills/architecture/references/design-contract.md:20-25` (the "Inputs
  and output" numbered list) — insert a step: identify the target platform(s) from the
  request/constraints, then read the matching section(s) of
  `references/platform-guidance.md` before drafting Tokens/Components
**Dependencies:** none
**Implementation notes:** keep each platform section scoped to what a design-contract pass
actually needs (tokens, components, interaction states, accessibility floor per platform)
— not a general iOS/Android development tutorial; mirror `design-contract.md`'s own
"Contract sections" structure (tokens, components/interaction, accessibility floor) per
platform so the two files read as one system, not two unrelated documents.
**Rollback:** delete the new file, revert the one inserted line in `design-contract.md`
**Preconditions:** none
**Verification:**
- Run: `python tools/test_referenced_paths.py`
- Expect: exits 0 — the new cross-link resolves to a real file
**Done when:** `platform-guidance.md` exists with Web/iOS/Android sections and
`design-contract.md`'s Inputs list references it by relative path

### Task 2: Wire Figma MCP into `architecture`'s tools and grounding procedure
**Purpose:** today Figma is configured repo-wide in `.mcp.json` but `architecture`'s
`allowed-tools: Read Grep Glob Bash` cannot call it — the skill that would use Figma for
design grounding has no permission to.
**Files:**
- Modify: `.claude/skills/architecture/SKILL.md:7` — extend `allowed-tools` to add
  `mcp__figma__get_design_context mcp__figma__get_screenshot mcp__figma__get_variable_defs
  mcp__figma__get_metadata` (none are `Write`/`Edit`/`NotebookEdit`, so
  `test_process_router.py`'s pre-approval ban is unaffected)
- Modify: `.claude/skills/architecture/references/design-contract.md` — new subsection
  under "Inputs and output" ("Ground in the source file"): when the request or an existing
  `DESIGN.md` names a Figma file/link, call `get_design_context`/`get_variable_defs` for
  real tokens and `get_screenshot`/`get_metadata` for real layout, before inventing a
  token or component — this directly extends the file's existing "Do not invent a token,
  component variant, or interaction merely to make the page look complete" rule with a
  concrete mechanism instead of leaving it to memory
**Dependencies:** 1 (same file, `design-contract.md`, edited serially; also references
`platform-guidance.md` by name)
**Implementation notes:** exact tool names matter — `test_portability_contract.py` (Task
3) requires the literal strings used here to also be the ones registered in the contract
**Rollback:** revert both file edits
**Preconditions:** none
**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: exits 0 — `architecture`'s required design-QA markers (unchanged) and the
  "does not pre-approve Write or Edit" check both still pass
**Done when:** `architecture/SKILL.md`'s `allowed-tools` lists the 4 Figma MCP tool names
and `design-contract.md` names them in a concrete grounding step

### Task 3: Register the new MCP tool terms in the portability contract and all adapters
**Purpose:** `capability-layer-maintenance`'s non-negotiable contract point 3: "a
host-specific token in a skill must map through that [capabilities.json/adapters]
contract for every declared adapter" — Task 2 introduces 4 new host-specific tokens.
**Files:**
- Modify: `.claude/portability/capabilities.json` — add the 4 tool names to
  `source_term_capabilities`, each mapped to `"web_research"` (the existing capability;
  same bucket as `mcp__github__search_code`)
- Modify: `.claude/adapters/claude-code.json` — add the 4 names to
  `source_term_resolution`, each `"host-configured"` (matches the existing
  `mcp__github__search_code` entry)
- Modify: `.claude/adapters/codex.json` — add the 4 names, each `"host-managed"`
- Modify: `.claude/adapters/generic-agent.json` — add the 4 names, each `"host-managed"`
**Dependencies:** 2 (the terms must already exist literally in `architecture/SKILL.md`'s
text for `test_portability_contract.py`'s "every mapped term is used" check to pass)
**Implementation notes:** do NOT add a new capability name — `expected` in
`tools/test_portability_contract.py:41-45` is a hardcoded, exact-match set; adding a new
category means editing that test too, which is out of scope per the Architecture section
above. Reuse `web_research`.
**Rollback:** revert all 4 JSON files
**Preconditions:** Task 2 merged/present so the literal strings exist in a `SKILL.md`
**Verification:**
- Run: `python tools/test_portability_contract.py`
- Expect: exits 0 — specifically "source tool terms map to declared capabilities", all
  three "`<adapter>` resolves every host-specific source term" checks, and "every
  host-specific term used by a skill has a capability mapping" all pass
**Done when:** all 4 JSON files list the 4 new terms consistently and the suite is green

### Task 4: Add the path-scoped design-MCP rule
**Purpose:** the user explicitly asked for a rule connecting design work to the
respective MCP; this also gives the Figma-grounding guidance standing-constraint reach
beyond `architecture`'s own procedure — e.g. `refactoring`'s design-QA sweep or
`implementation` cross-checking a built surface against `DESIGN.md` should also prefer
real Figma data over invented values, and a rule (unlike a skill body) applies passively
whenever Claude touches the file, not only when `architecture` is invoked.
**Files:**
- Create: `.claude/rules/design-mcp.md` — `paths: ["DESIGN.md", "docs/specs/**/*.md"]`
  frontmatter (loads lazily, not every session, per `templates/rules.md`'s own guardrail);
  body: one standing constraint — when a design surface (web, iOS, or Android) has a
  linked Figma file, ground tokens/components/screenshots via the `mcp__figma__*` MCP
  tools rather than inventing them; Figma is the one MCP configured in this repo that
  covers all three platforms, so no per-platform MCP choice is needed; points at
  `architecture/references/design-contract.md` and `platform-guidance.md` for the full
  procedure
**Dependencies:** 1 (references `platform-guidance.md` by name; written after it exists so
the reference is accurate)
**Implementation notes:** written as a fact/constraint, not a numbered procedure — that is
the dividing line `templates/rules.md` draws between a rule and a skill; keep it short,
this is guidance not a walkthrough
**Rollback:** delete the file
**Preconditions:** Task 1 done
**Verification:**
- Run: `python tools/run_checks.py --scoped`
- Expect: no new failure introduced (no automated suite currently validates `.claude/rules/*.md` content — confirmed by inspection during framing — so this is a smoke check, not a targeted assertion)
**Done when:** the file exists, parses as valid YAML frontmatter + Markdown body, and
states the constraint in one paragraph without step numbering

### Task 5: Fix `templates/DESIGN.md`'s stale skill reference and add a Platform line
**Purpose:** `templates/DESIGN.md:8` still says `` `designer` treats that as a blocking
question `` — `designer` was merged into `architecture` on 2026-08-21
(`decisions/2026-08-21-notion-architecture-merge.md`) and no longer exists as a skill
name; found while reading this exact file family for this task. Same file also needs a
one-line hook for a project to state its target platform, so a forked `DESIGN.md`
immediately signals which `platform-guidance.md` section applies.
**Files:**
- Modify: `templates/DESIGN.md:8` — `designer` -> `architecture`
- Modify: `templates/DESIGN.md` (top, under "## What this is") — add a `**Platform:**
  [web / iOS / Android / more than one]` line
**Dependencies:** none
**Implementation notes:** one-word rename plus one new line; no structural change to the
template
**Rollback:** revert the file
**Preconditions:** none
**Verification:**
- Run: `python tools/test_referenced_paths.py`
- Expect: exits 0
- Also confirm by inspection: `designer` no longer appears in the file, `architecture`
  does, and a `**Platform:**` line exists under "What this is"
**Done when:** both edits are present and the referenced-paths suite is still green

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [ ] II Test first — see Complexity tracking; no dedicated test is *written* by this plan
- [x] III Smallest change — no refactor beyond what each task requires
- [x] IV Reversibility — every step is a plain text revert, nothing irreversible
- [x] V No silent degradation — no check is skipped; Task 4 names the one suite that
      cannot cover its target and says why
- [ ] VI Mechanism — see Complexity tracking for Task 4's rule
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
- **II** — this plan changes contract/reference text, not executable logic; the existing
  generic validators (`test_process_router.py`, `test_portability_contract.py`,
  `test_referenced_paths.py`) already assert the shape any future change of this kind must
  hold, and each task's Verification runs the one that covers it. No new test is warranted
  for prose additions with no branching logic.
- **VI** — Task 4's rule has no mechanical enforcement, confirmed during framing (no suite
  validates `.claude/rules/*.md` content, matching this repo's existing rules such as
  `docs-structure.md`/`llm-env.md`, neither of which is test-enforced either). The actual
  *mechanism* — MCP tool availability — is enforced by Tasks 2-3
  (`test_process_router.py` + `test_portability_contract.py`); the rule only adds the
  human-legible "why" on top of an already-enforced capability, which is the rule
  mechanism's normal shape in this repo.

## Verification (end to end)
After all 5 tasks: `python tools/run_checks.py --tier all --require-test` must exit 0 and
report a higher or equal green-check count than the current baseline, with no suite newly
skipped. This is `testing`'s stage-4 pass, run after `implementation` finishes all tasks —
not a task inside this plan.

## Approved

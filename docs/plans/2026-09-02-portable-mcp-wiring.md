# Portable MCP Wiring — Implementation Plan

**Goal:** Ship the MCP server entries the layer's skills and rules actually
depend on (figma, github, context7, sentry) with `.claude/install.py`, merged
into a target's own `.mcp.json` without overwriting it, and add a deterministic
check that stops `.mcp.json` and `.vscode/mcp.json` drifting.

**Source brief:** this session's request — "these MCPs and the wiring … should
also be portable and installable" — following the UI/UX-resources change that
pointed `architecture`'s design procedure at Figma-backed grounding.

**Slug:** `portable-mcp-wiring` (branch `feat/portable-mcp-wiring`)

**Risk:** **high (expected)** — `scope.py` vetoes on installer + packaging
surfaces (`.claude/install.py`, `pyproject.toml` payload path, `tools/test_package.py`).
To be confirmed by `python tools/scope.py --plan docs/plans/2026-09-02-portable-mcp-wiring.md`
once the plan is committed there. Not permission to skip Gate 2.

**Blast radius:** `.claude/install.py` (every future `install`/`upgrade` into a
target), the wheel payload, `.claude/hooks/check_config_json.py` (a `lint`
check that gates every auto-commit), `templates/`, plus doc files
(`CLAUDE.md`, `.claude/README.md`, `harnesses.json`, `MEMORY.md`). No product
code — this repo ships none. No hook registration change, no lifecycle stage,
no new skill/agent/command.

**Rollback:** every change is additive to tracked text/JSON.
`git revert` / `git checkout -- <path>` on any subset cleanly restores prior
behaviour. Worst landing state (half the tasks merged): a target could receive
`templates/mcp-servers.json` without the `install.py` wiring that reads it —
inert (an unused template file), not harmful. No migration, no data, no
irreversible step.

---

## Context — why this change

`.claude/install.py` copies skills, rules, hooks, agents, commands, tools, the
portability contract and adapters into a target repo. It does **not** copy any
MCP configuration. Yet the layer it installs is wired to MCP tools:

| Consumer | MCP dependency | Evidence |
|---|---|---|
| `architecture` skill `allowed-tools` + `references/design-contract.md` | `mcp__figma__get_design_context` / `_screenshot` / `_variable_defs` / `_metadata` | 25 `figma` refs across 3 `.md` files; mapped in `.claude/portability/capabilities.json` |
| `.claude/rules/design-mcp.md`, new `.claude/rules/ui-ux-resources.md` | Figma MCP for design grounding | rule bodies |
| `research` / `engineering-standards` | `mcp__github__search_code`, `mcp__context7__query-docs` | 11 `github`, 5 `context7` refs; both mapped in the portability contract |
| `.claude/rules/error-monitoring.md` | `.mcp.json`'s `sentry` entry (named explicitly) | rule body |

A freshly installed target therefore gets `architecture` telling the model to
call `mcp__figma__*` and `error-monitoring.md` telling it Sentry "is already
wired as an MCP server in this layer" — with nothing on disk that starts those
servers. The layer's own most-repeated failure class is *a name that resolves
to nothing*; this is that class, one level down, in the runtime wiring.

Two constraints from the repo's own memory shape the fix:

- **`MEMORY.md` §"MCP and local configuration":** `.mcp.json` and
  `.vscode/mcp.json` "use different schemas and must remain synchronized
  deliberately" — a hand-sync with no mechanism behind it.
- **`install.py` precedent (`EXCLUDE_FILES`, `SEED_SOURCE`/`CODEOWNERS.seed`):**
  this repo's *opinion* is not shipped. `.mcp.json` carries 14 servers;
  `notion`, `linear`, `filesystem`, `git`, `fetch`, `memory`,
  `sequential-thinking`, `time`, `playwright`, `chrome-devtools` are referenced
  by **no** skill/rule/command and are the installing repo's own choice.

## Approach

1. **A curated seed, not the dev file.** New `templates/mcp-servers.json`
   holds exactly the four load-bearing servers in Claude Code's `mcpServers`
   schema, with env-var placeholders (`${GITHUB_TOKEN}`), no literal secrets.
   This is the payload source — mirrors `templates/CODEOWNERS.seed`, which
   exists precisely because shipping the repo's real file "still LOOKS like
   [config] either way". The root `.mcp.json` stays the dev environment and is
   **not** added to the payload.

2. **Merge, never overwrite.** `install.py` gains an `mcp-merge` action:
   parse the target's `.mcp.json` (if any), add only the seed servers whose
   key is absent, leave every existing entry untouched, write back with
   `json.dumps(..., indent=2)`. Parsed both sides, never string-spliced — same
   rule and rationale as `merge_settings` (a stray comma silently disables MCP
   for the host). A target with no `.mcp.json` gets one containing just the
   four.

3. **Deterministic drift check.** Extend `.claude/hooks/check_config_json.py`
   (already the guard that `.mcp.json` parses; already a `lint` check in
   `project-checks.json`) with three schema-aware assertions:
   - every server in `templates/mcp-servers.json` is also configured in the
     root `.mcp.json` (the seed can't name a server the dev env doesn't run);
   - `.mcp.json` (`mcpServers` keys) and `.vscode/mcp.json` (`servers` keys)
     declare the **same server set** — the "synchronized deliberately" from
     `MEMORY.md`, now mechanical;
   - `templates/mcp-servers.json` contains only names from the sanctioned set
     (no `notion`/`linear`/etc. creeping into the payload).

4. **`.vscode/mcp.json` is not itself shipped** — explicit non-goal. It is one
   editor's projection with a different schema; `.mcp.json` is the
   host-neutral Claude Code standard the layer's contract targets. The drift
   check keeps the repo's own two files honest; a target's VS Code config is
   the target's.

5. **Make it discoverable.** `harnesses.json` `canonical_paths` gains
   `mcp_seed: "templates/mcp-servers.json"` and `mcp_config: ".mcp.json"` so a
   non-Claude host bridging the layer can find the wiring. Docs updated where
   the `settings.json` merge is already described.

**Alternative rejected:** filter the root `.mcp.json` down to the four servers
at install time and keep it as the single source. Rejected because the wheel
payload would then carry a 14-server file that "LOOKS like the layer's MCP
config" even though install discards ten of them — the exact failure
`CODEOWNERS.seed` was created to avoid.

## Tech stack and constraints

- Pure `.claude/` + `templates/` + `tools/` + root-doc edits. No product code.
- **Must not** change any skill's `allowed-tools`, the portability contract's
  capability set, or `test_portability_contract.py`'s hardcoded name sets.
- **Must not** register or rename a hook; `check_config_json.py` stays a
  `lint`-tier check invoked exactly as it is now.
- `install.py` invariants hold: `--dry-run` writes nothing; second run
  rewrites nothing; refuses to install into itself; `PRESERVE`/`MERGE`
  disjoint; `write_manifest` records the new action's target path as
  layer-owned.
- New JSON must satisfy `check_config_json.py` (parses) and
  `tools/test_no_slop.py --scope layer`.
- Set `PYTHONIOENCODING=utf-8` before every tool script (Windows).

---

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — behaviour changes are in `install.py` / `check_config_json.py`; Tasks 2-3 write the `test_install.py` / `check_config_json.py` assertions and prove them red (one-sided drift edit) before the code
- [x] III Smallest change — additive constant + one action + three assertions; no `install.py` refactor, no hook re-registration
- [x] IV Reversibility — every change is `git revert`-able tracked text/JSON; no migration, no external action; worst half-merged state is an inert template file
- [x] V No silent degradation — no check is skipped; the full tier runs at Task 5
- [x] VI Mechanism — the "`.mcp.json` ⇔ `.vscode/mcp.json` stay in sync" rule is enforced by `check_config_json.py`, not prose
- [x] VII Secrets — the seed carries only the `${GITHUB_TOKEN}` placeholder `.env.example` already documents; no literal credential

## Complexity tracking
_All boxes ticked; no article exception taken._

---

## File map

| Path | Action | Owns afterward |
|---|---|---|
| `templates/mcp-servers.json` | Create | The shippable MCP server set (figma, github, context7, sentry), Claude Code `mcpServers` schema, placeholder auth only |
| `.claude/install.py` | Modify | `SHIPPED_MCP_SERVERS` constant; `.mcp.json` in the merge-source payload; `mcp-merge` action in `plan()`/`apply()`; `merge_mcp()` helper; manifest records the target `.mcp.json`; module docstring covers the new rule |
| `.claude/hooks/check_config_json.py` | Modify | The three MCP drift assertions above, alongside the existing config-JSON checks |
| `harnesses.json` | Modify | `canonical_paths.mcp_seed` + `canonical_paths.mcp_config` |
| `tools/test_install.py` | Modify | Coverage: seed lands on a clean target; a target's own `.mcp.json` entries survive and missing shipped servers are added; `--dry-run` writes nothing; second run is a no-op |
| `tools/test_package.py` | Modify | Payload carries `templates/mcp-servers.json`; the shipped seed has no `notion`/`linear`/`filesystem` server |
| `CLAUDE.md` | Modify | One line near the existing `.mcp.json`/`.vscode/mcp.json` "kept in sync by hand" note — they now travel (filtered) and a check guards the sync |
| `.claude/README.md` | Modify | One line in "Installed into another repository", beside the `settings.json`-merge sentence |
| `MEMORY.md` | Modify | §"MCP and local configuration" — the sync is now enforced by `check_config_json.py`; the shippable set is the four load-bearing servers |
| `docs/plans/2026-09-02-portable-mcp-wiring.md` | Create | this plan, at its canonical path |
| `TASK.md` | Modify | ledger row for this unit (+ the UI/UX row it rides with) |

**Also on this branch** — the small UI/UX-resources change that motivated the
MCP question, carried here rather than on a separate branch since it is what
made the Figma-MCP dependency concrete:

| Path | Action | Owns afterward |
|---|---|---|
| `.claude/rules/ui-ux-resources.md` | Create | path-scoped pointer to the external UI/UX design-intelligence repos (UI UX Pro Max, Taste Skill, Awesome Claude Design) + "find current ones on the fly" |
| `.claude/skills/architecture/references/design-contract.md` | Modify | Inputs step 5 — consult those references before inventing tokens |

This plan already lives at its canonical path (`docs/plans/2026-09-02-portable-mcp-wiring.md`),
so `tools/analyze.py --slug portable-mcp-wiring` and `tools/resume.py` can read
it. Tasks below start at the first real change.

## Progress
- [x] Task 1 — `templates/mcp-servers.json` curated seed
- [x] Task 2 — `install.py`: ship + merge `.mcp.json` from the seed
- [x] Task 3 — `check_config_json.py`: MCP drift assertions
- [x] Task 4 — `harnesses.json`: expose the MCP paths
- [x] Task 5 — Docs: `CLAUDE.md`, `.claude/README.md`, `MEMORY.md`

### Deviations from the plan as written
- **`SEED_SOURCE` gained a `.mcp.json` → `templates/mcp-servers.json` entry**
  (not in the file map). Needed because `write_manifest` hashes owned paths
  through `seed_source()`; without it the manifest would record the 14-server
  dev `.mcp.json`'s hash and `upgrade` would read every target as locally
  edited. Same mechanism `CODEOWNERS` already uses.
- **`uninstall`'s `protected_names` gained `".mcp.json"`** — a merged MCP
  config must not be deletable by `uninstall`, exactly as `settings.json`
  (MERGE) is protected.
- **`test_package.py` assertions landed in Task 5** (the plan offered Task 2 or
  5); co-located with the payload-carries / no-dev-`.mcp.json` checks.
- Task 0 (relocate the plan) folded into handoff scaffolding — this file is
  already at the canonical path.

## Tasks

### Task 1: Curated MCP server seed
**Purpose:** a shippable MCP config that is the layer's requirement, not its opinion
**Files:**
- Create: `templates/mcp-servers.json` — `{"mcpServers": {figma, github, context7, sentry}}`, copied field-for-field from the matching entries in the root `.mcp.json` (github keeps `"Authorization": "Bearer ${GITHUB_TOKEN}"`; figma/sentry are `type:"http"` + `url`; context7 is the `npx @upstash/context7-mcp` stdio entry)
**Dependencies:** none
**Implementation notes:** no literal secret — only the `${GITHUB_TOKEN}`
placeholder, which `.env.example` already documents. A header comment is not
valid JSON; the "replace me / these are the layer's required servers" note goes
in the accompanying docs, not the file.
**Rollback:** delete the file
**Preconditions:** none
**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python .claude/hooks/check_config_json.py`
- Expect: `OK: templates/mcp-servers.json`, all config JSON valid
**Done when:** the file parses and its four server blocks byte-match the
corresponding blocks in `.mcp.json`

### Task 2: install.py ships and merges `.mcp.json`
**Purpose:** a target install receives the four servers without losing its own
**Files:**
- Modify: `.claude/install.py` — add `SHIPPED_MCP_SERVERS = ("figma", "github", "context7", "sentry")`; add `templates/mcp-servers.json` to `EXTRA_PAYLOAD`; add `merge_mcp(seed_text, target_text) -> (merged_json, added_names)`; emit a `("​.mcp.json", "mcp-merge")` action from `plan()`; handle it in `apply()` (read target if present, union missing seed servers, write `indent=2`); include `.mcp.json` in `write_manifest`'s owned set for the `mcp-merge` action; extend the module docstring's rule list
- Modify: `.claude/install.py` — `MERGE`-adjacent: `mcp-merge` must not make `.mcp.json` a `PRESERVE` or `MERGE` member (keep those sets meaning what they mean); mirror `merge_settings`'s JSON-parse-both-sides guard and its "only ever adds" contract
**Dependencies:** 1
**Implementation notes:** seed source is `templates/mcp-servers.json`, never the
root `.mcp.json` (which is not in the payload). Target with no file → write the
seed as-is. Target with the file → add only absent server keys; never touch an
existing entry's value even if it differs. `--dry-run` path already routes
through `plan()` only, so it stays write-free by construction; assert it.
**Rollback:** revert the `install.py` diff; `templates/mcp-servers.json` from
Task 1 becomes inert
**Preconditions:** Task 1 file exists
**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_install.py`
- Expect: existing assertions still pass; new ones (clean-target seed lands,
  keeper-target own entries survive + missing added, dry-run writes nothing,
  second plan rewrites nothing) pass
**Done when:** `test_install.py` is green with the new coverage and a manual
`python .claude/install.py --into <tmp> --dry-run` lists `.mcp.json` and writes nothing

### Task 3: check_config_json.py — MCP drift assertions
**Purpose:** the `.mcp.json` / `.vscode/mcp.json` hand-sync gets a mechanism
**Files:**
- Modify: `.claude/hooks/check_config_json.py` — after the existing per-file
  loop: (a) load `templates/mcp-servers.json`, `.mcp.json`, `.vscode/mcp.json`;
  (b) FAIL if any seed server key is absent from `.mcp.json`'s `mcpServers`;
  (c) FAIL if `set(.mcp.json mcpServers)` != `set(.vscode/mcp.json servers)`;
  (d) FAIL if `templates/mcp-servers.json` names a server outside
  `{figma, github, context7, sentry}`. Each with a one-line reason string in
  the file's existing `FAIL:`/`failures.append` style.
**Dependencies:** 1
**Implementation notes:** all three files are optional-guarded (`if
path.is_file()`), matching how the script already treats `settings.json` /
`hooks_registry.json`. Keep the check read-only and fail-closed (`sys.exit(1)`
via the existing `failures` list). Do not add a new registered hook — this is
the same script, same `lint` invocation.
**Rollback:** revert the diff
**Preconditions:** Task 1 file exists; `.mcp.json` and `.vscode/mcp.json`
already agree on their 14 servers (verified this session)
**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python .claude/hooks/check_config_json.py`
- Expect: passes now; then temporarily add a server to `.vscode/mcp.json` only
  and confirm it FAILs with the parity message; revert
**Done when:** the check is green on the real tree and red on a proven
one-sided edit

### Task 4: Expose the MCP paths in harnesses.json
**Purpose:** a bridging host can discover the wiring like any other canonical path
**Files:**
- Modify: `harnesses.json` — add to `canonical_paths`:
  `"mcp_seed": "templates/mcp-servers.json"`, `"mcp_config": ".mcp.json"`
**Dependencies:** 1
**Implementation notes:** `test_portability_contract.py` reads
`canonical_paths` with keyed `.get(...)` lookups, not an exhaustive
`set(...) ==`, so extra keys are safe — confirm by reading its
`canonical_paths` assertions before editing.
**Rollback:** revert the two lines
**Preconditions:** none
**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_portability_contract.py &&
  PYTHONIOENCODING=utf-8 python tools/test_harness_contract.py`
- Expect: both green
**Done when:** both suites pass with the new keys present

### Task 5: Docs — CLAUDE.md, README, MEMORY
**Purpose:** the three places that describe install behaviour match reality
**Files:**
- Modify: `CLAUDE.md` — the line stating `.mcp.json` / `.vscode/mcp.json` are
  "kept in sync by hand and can [drift]": they now travel with `install.py`
  (filtered to the load-bearing servers) and `check_config_json.py` guards the
  sync
- Modify: `.claude/README.md` — "Installed into another repository": one
  sentence beside the `settings.json`-merge line — `.mcp.json` is merged by
  server name from `templates/mcp-servers.json`, never overwriting a target's own
- Modify: `MEMORY.md` — §"MCP and local configuration": the sync is enforced by
  `check_config_json.py`; the shippable set is figma/github/context7/sentry;
  the rest of `.mcp.json` is the installing repo's choice
**Dependencies:** 2, 3
**Implementation notes:** `test_package.py` asserts payload carries
`templates/mcp-servers.json` and NOT a `notion`/`linear` server — add those two
assertions here (co-located with the file-map change that motivates them) or in
Task 2; pick one and note it. Keep every entry minimal — `MEMORY.md` and
`CLAUDE.md` load every session.
**Rollback:** revert the doc diffs
**Preconditions:** Tasks 2-3 landed
**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_package.py &&
  PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
- Expect: `PASS` on the full tier; `test_referenced_paths.py` resolves the new
  `templates/mcp-servers.json` mentions
**Done when:** full tier green and the three docs describe the shipped behaviour

---

## Verification (end to end)

1. `PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
   → `PASS`, with `test_install.py`, `test_package.py`,
   `check_config_json.py`, `test_portability_contract.py`,
   `test_harness_contract.py` all green.
2. Clean-room install:
   `python .claude/install.py --into <tmp-git-repo>` → `<tmp>/.mcp.json` exists
   with exactly figma/github/context7/sentry.
3. Preserve check: seed a `<tmp>/.mcp.json` with one custom server + a
   deliberately different `figma` url, install, confirm the custom server and
   the target's `figma` value both survive and the three missing servers are
   added.
4. Idempotence: run the install again → "rewrites nothing".
5. Drift check: add a server to `.vscode/mcp.json` only →
   `check_config_json.py` exits 1 with the parity message; revert.

## Open questions

_None. The shippable server set is determined by grep (only figma, github,
context7, sentry are referenced by any skill/rule/command); `.vscode/mcp.json`
non-portability and the curated-seed-over-filtered-dev-file choice are settled
against the `EXCLUDE_FILES` / `CODEOWNERS.seed` precedent in `install.py`._

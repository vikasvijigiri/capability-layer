# Notion "Agentic Workflows (IDE)" — full audit, 2026-08-20

**Source:** Notion page *Agentic Workflows (IDE) — Universal Adaptive SDLC
v2* (`3b9b1c6b-5e27-81b5-ba18-d753031e068d`), fetched in full via the Notion
MCP connector this session. 30 Primary Objectives (§0) plus 25 sections of
target architecture (§1-25). `docs/objectives.md` captured only the first 10
objectives as of 2026-08-16 and none of §1-25 — this document is the first
comparison against the complete source.

**Method.** Read the full page once (fetched inline, not paraphrased from
memory). Compared each objective and architecture section against this
repo's actual, currently-observable state — grep hits, file counts, hook
registrations, and direct quotes from this repo's own code where a claim
needed grounding rather than impression. Static comparison, local execution
evidence only; no live-host or paid-eval measurement was re-run for this
pass (objective 2's $81 trigger measurement stays its own decision, per
`HANDOFF.md`).

## Part 1 — Objectives 11-30, first grading

No dedicated instrument exists for most of these yet (see `docs/objectives.md`).
Graded qualitatively from repo evidence; **Amber** means partial/unmeasured
rather than failing.

| # | Objective | Grade | Evidence |
|---|---|---|---|
| 11 | World-class engineering | Amber | This session's own chain (evidence-gated verification, red-green regression proof, independent dispatched review) is a real instance of the discipline; not every corner of the repo is held to it equally — e.g. `01-context-cost.py` has zero test coverage anywhere in the repo (grepped, confirmed) despite being live-wired since before this session. |
| 12 | Production-grade by default | Amber | The layer's own tooling is heavily tested (constitution Article II, mutation-tested fixes throughout `ISSUES.md`), but coverage is uneven — same `01-context-cost.py` gap as #11. |
| 13 | Universal / generic | Green | `harnesses.json` + `.claude/adapters/` (claude-code, codex, generic-agent) + `.claude/portability/capabilities.json`; the 2026-08-16 audit's own verdict was "generic is closed." |
| 14 | Portable | Green | `tools/test_install.py`/`test_package.py` prove a fresh install green in a Python and a Node target; "Make the layer portable" closed in `TASK.md` with before/after payload sizes. |
| 15 | Stage-agnostic | Amber | `repo-recon` exists for unread/half-finished repos; no evidence of testing against a genuinely broken or undocumented target repo specifically. |
| 16 | Repository-agnostic | Green-Amber | `repo-recon` skill + `tools/recon.py` discover structure before acting; not exercised this session against an unfamiliar repo to confirm. |
| 17 | Non-destructive integration | Green | `install.py`'s `PRESERVE` list, the `uninstall` verb (`decisions/`, `ISSUES.md` 2026-08-09 path-traversal fix on exactly this feature). |
| 18 | Adaptive, not prescriptive | Amber | `tools/scope.py` (small/major, low/medium/high) + the entry classifier both adapt routing to signal — but the two mechanisms disagreed until this session's `fix/router-progress-consistency` unit closed the *specific reproduced case*, not the whole class (recorded in `HANDOFF.md`). |
| 19 | Idempotent and repeatable | Amber | `install.py --dry-run` is proven byte-identical; no test exercises running the full chain twice on the same unit to confirm convergence rather than duplication. |
| 20 | Backward-compatible where practical | Unmeasured | No versioning or compatibility-testing convention observed for the layer's own contract surface (skill/hook schema changes). |
| 21 | Secure by default | Green | `security_gate.py` (5 clauses), `pre-commit/01-secret-scan.py`, `02-branch-guard.py`, `03-attribution-guard.py`, `pre-deploy/01-spend-guard.py`, `tools/deps.py` licence gate — the deepest-covered objective in the repo. |
| 22 | Observable and auditable | Amber | `LOG.md`/`ISSUES.md`/`tools/chain.py`'s ledger cover decisions and failures; no single place answers "what happened in run N" without reading multiple files — see Part 2's telemetry gap. |
| 23 | Evidence-driven | Green | This is the layer's central discipline — `verifying-work`'s HARD-GATE, `CLAUDE.md`'s "never report a check as passing that was not actually run." Strongest-held objective in the repo. |
| 24 | Self-adapting and self-healing | Amber | `systematic-debugging` exists; `chain.py`'s stall detection escalates rather than auto-repairs — likely correct per objective 1 (ask only when necessary), but worth confirming the boundary is deliberate everywhere it applies. |
| 25 | Technology-agnostic | Green-Amber | `install.py` seeds Python lint config only into hosts that have Python (`TASK.md`, "Audit all ten objectives" unit); not verified against a non-Python, non-Node stack. |
| 26 | Low-coupling / composable | Amber | Real counter-evidence exists: the router-disagreement and the overlapping `spec-reviewer`/`test-verifier` dispatches (both closed this session) were coupling defects by this exact definition. The pattern of duplicated `_load()` helpers across 4 tool files is an accepted, explicit exception (not a violation — see `docs/plans/2026-08-20-router-progress-consistency.md`'s Grounding). |
| 27 | Progressively adoptable | Green | `install.py` does not require rewriting the target repo; additive by design. |
| 28 | Safe under uncertainty | Green | `[NEEDS CLARIFICATION]` markers, `EnterPlanMode`/`ExitPlanMode`, the entry classifier's `entry-open` routing — a well-instrumented objective. |
| 29 | No hardcoded project truth | Green-Amber | `templates/CODEOWNERS.seed` + `SEED_SOURCE` indirection (from the 2026-08-16 audit unit) is a direct, on-point implementation of this exact objective. |
| 30 | Continuous improvement without instability | Green | `tools/bench.py --save` baselines *comparisons*, never *judges*; `budget.ELAPSED_CEILING_HOURS` was explicitly **not** refit from one session's noisy 118-turn outlier (`HANDOFF.md` Pending #3) — a textbook instance of "preventing noisy, speculative... learning from changing core behavior." |

**Rough count:** 8 green, 2 green-amber, 8 amber, 1 unmeasured, 0 red — better
than objectives 1-10's 2026-08-16 profile (4 green / 5 amber / 1 red), though
not directly comparable since these were never measured before and the
grading here is qualitative, not instrumented.

## Part 2 — Architecture sections (§1-25): verified structural deltas

Three real, confirmed gaps against the target architecture — not impressions,
each checked against the actual tree:

### Gap A — No E0-E5 execution-level router (§3)

The target's core routing primitive: six levels from `E0` (direct answer) to
`E5` (full workflow/team), chosen by evidence not complexity. **This repo
admits not having it, in its own source**:

> `.claude/hooks/user-prompt/01-entry-classifier.py:420` — *"...and saying so
> is the one execution level this layer never had..."*

`HANDOFF.md`'s S1 unit (2026-08-14) explicitly deferred it: *"the router
(E0–E5) and the surface trim are S2/S3 and are not in scope here."* Still
true as of this session — grepped for `E0`/`E1`.../`execution level`
repo-wide, only that one self-aware comment and no implementation. The entry
classifier gets partway there (small/open/task/direct/silent — five shapes,
not six levels, and it classifies *prompt shape* rather than *how much
execution machinery to spend*), but it is not the same primitive the target
describes.

### Gap B — No deterministic context-budget hook (§7, §2.1)

The target names `context-budget` as one of 10 hook families, whose job is to
*"prevent accidental context explosion"* — a gate, not a report. This repo's
closest match, `post-tool/01-context-cost.py` (plus this session's own
`02-skill-cost.py`), is explicitly a **reporter**: its own docstring states
*"Reports, never gates"* and explains why (a `PreToolUse` version was tried
and rejected — see the hook's own "Reports, never gates" section, which cites
`test_hook_standards.py` refusing a silent-allow `PreToolUse`). So the
target's specific ask — a hook that *prevents* an oversized call before it
happens — was considered and deliberately not built this way. Worth
recording as a **reasoned Extend**, not silently closing the gap: the
alternative (auto-blocking a large tool call) was rejected once already for a
concrete reason, and any future attempt needs to reckon with that reasoning
rather than reopen it blind.

### Gap C — No unified telemetry schema (§21)

The target specifies one schema per run: `run_id, task_type, execution_level,
model, skills_loaded, agents_spawned, tools_called, api_call_count,
context_tokens, input_tokens, output_tokens, latency, parallelism,
cache_hits, cache_misses, repeated_operations_avoided, verification_level,
retries, escalations, success, quality_signal`. Grepped repo-wide for
`run_id`, `quality_signal`, `cache_hits`, `context_tokens` — no hits outside
this document and one 2026-08-03 design spec
(`docs/specs/2026-08-03-research-run-substrate-design.md`, unread this pass,
worth checking for prior art before building anything new). What exists
instead is **three uncoordinated partial counters**: `bench.py`'s
`session_calls()` (shell calls, chars, repeats), `01-context-cost.py`'s
per-call warnings, and this session's own `02-skill-cost.py` (skill
invocations, `SKILL.md` chars, unattributed). Each answers a narrow question;
none share a schema, a run boundary, or a `run_id`. `tools/chain.py`'s ledger
(`chain-ledger.jsonl`) is the closest thing to a per-run record but tracks
chain *state* (BUILD/WAITING_DELIVERY/etc.), not the target's cost/quality
fields.

### Catalogue sizes — compared, not necessarily gaps

| Catalogue | Target | This repo | Verdict |
|---|---|---|---|
| Skills | "~10-15 core" (§4 table) | 14 (`ls .claude/skills`) | **Keep** — within range. Named by SDLC *stage* (writing-plans, executing-plans, verifying-work...) rather than the target's example list of *domain* names (implementation, testing, refactoring...) — a reasoned **Extend**: this layer's whole purpose is enforcing an SDLC chain, so stage-shaped skills fit its job better than the target's generic example set, which is presented as illustrative ("Skills should describe capabilities, not individual tasks") rather than mandatory. |
| Agents | "~6-8 core" (§4 table) | 11 custom `.md` files (plus several harness-native types: `general-purpose`, `Explore`, `Plan`) | **Amber** — above the stated range by 3-5. Plausibly reasoned (narrow single-lens reviewers — `spec-reviewer`, `test-verifier`, `diff-reviewer`, `security-reviewer`, `architecture-reviewer`, `release-verifier` — mirror `code-review`'s own "pick the lens by what changed" philosophy rather than one broad reviewer), but this reasoning has never been written down as a decision. Worth a `decisions/` entry either way: confirms the count is deliberate, or flags consolidation as a real candidate. |
| Hook families | 10 named (session-init, prompt-intake, context-budget, permission-security, pre-tool, post-tool, pre-edit, post-edit-validation, stop-finalization, telemetry) | 10 logical families in `hooks_registry.json` (session-start, user-prompt, post-run, post-run-steps, pre-commit, pre-edit, pre-deploy, on-artifact-create, pre-run, post-tool) mapped onto 5 native Claude Code events | **Amber** — same count, different shape. `context-budget` and `telemetry` have no dedicated family (Gaps B and C above); `permission-security` is spread across `pre-commit`/`pre-edit`/`pre-deploy` rather than unified, functionally covered but not named as the target names it; `post-edit-validation` (target: format/lint/targeted-validation trigger on any edit) is narrower here (`on-artifact-create` only nudges hook self-testing, not general lint-on-edit). |

## Part 3 — Candidate optimization units

Four independent, differently-scoped candidates. Deliberately not bundled
into one plan — per this repo's own `writing-plans` C1 rule, work that spans
subsystems this cleanly separable gets separate plans, not one that tries to
be all of them.

1. **Unified telemetry schema** (closes Gap C). Consolidate
   `session_calls()`, `skill_body_cost()`, and the chain ledger's run-shaped
   facts into one per-run record matching (a useful subset of) the target's
   schema. Highest leverage: every other objective's grading (2-10) already
   depends on ad hoc versions of exactly this data.
2. **E0-E5 execution-level classification** (closes Gap A). Extend
   `01-entry-classifier.py`'s prompt-shape classification into an explicit
   execution-level estimate, OR write down why the five-shape classifier is
   the right-sized answer for this repo and the six-level model is not
   worth building. Either output closes the gap — a decision record is a
   valid closure, not just code.
3. **Agent-catalogue decision record** (the Amber "Agents: 11 vs ~6-8"
   finding). Cheapest of the four: write the reasoning down, or consolidate
   if it doesn't hold up under scrutiny.
4. **Test coverage for `01-context-cost.py`** (the concrete #11/#12 gap
   found). Smallest, most mechanical: it is a live-wired hook with zero
   tests anywhere in the repo, unlike its own sibling `02-skill-cost.py`
   which this session gave 7 test cases.

## What this pass did not do

- No paid live-trigger measurement re-run (objective 2 stays at its
  2026-08-16 grade; `HANDOFF.md` already names the $81 decision as owed
  separately).
- No re-grade of objectives 1-10 against current code — several have almost
  certainly moved (objective 8's router-disagreement class partially closed;
  objective 4/5's counters gained a second instrument this session) but
  re-measuring all ten needs the same instruments `docs/objectives.md`
  already names, run fresh, not asserted from memory here.
- Did not read `docs/specs/2026-08-03-research-run-substrate-design.md` —
  flagged above as likely prior art for candidate 1, worth reading before
  planning it rather than starting from a blank page.

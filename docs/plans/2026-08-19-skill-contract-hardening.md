# Skill Contract Hardening Implementation Plan

**Goal:** Strengthen the local debugging skill using the verified ECC comparison, close the release approval tool mismatch, and make the remaining evidence boundaries executable or explicit.

**Source brief:** The current skill comparison between `.claude/skills/systematic-debugging/SKILL.md` and ECC's `agent-introspection-debugging/SKILL.md`, plus the current repository audit findings.

**Slug:** skill-contract-hardening

**Risk:** low — `python tools/scope.py --plan docs/plans/2026-08-19-skill-contract-hardening.md` reports `low` with no forced clause over 6 declared paths. The release approval contract is operationally sensitive, so Task 3 remains serialized after the first round despite the computed scope.

**Blast radius:** All sessions that invoke `systematic-debugging`; all sessions that reach the `releasing` Gate 2 approval; the skill-layer contract tests; no product runtime code.

**Rollback:** Revert the plan's skill and validator changes together. This restores the current debugging/release contracts and leaves no migration, generated artifact, adapter status change, or external side effect.

**Architecture:** Keep the local skill's code-debugging discipline as the canonical procedure and add only the missing agent-run capture/reporting layer from the verified ECC comparison. Keep host portability claims qualified: no Codex or generic-agent adapter becomes verified without a real host-specific conformance command and receipt.

**Tech stack and constraints:** Markdown skill contracts, Python repository validators, existing `test_process_router.py`, existing adapter manifests. No copying of ECC text wholesale, no new parallel skill registry, no paid live trigger run without explicit approval, no change to `bridge-required-unverified` statuses from static evidence.

## File map

| File | Action | Responsibility after the change |
|---|---|---|
| `.claude/skills/systematic-debugging/SKILL.md` | Modify | Unified code-failure and agent-run-failure workflow with capture, diagnosis, bounded recovery, verification, and report output |
| `.claude/skills/releasing/SKILL.md` | Modify | Gate 2 declares the approval tool it must invoke |
| `tools/test_process_router.py` | Modify | Enforces the debugging contract markers, removes stale-count wording, and requires Gate 2 tool availability |
| `tools/test_portability_contract.py` | Modify | Keeps adapter-status claims tied to actual conformance evidence and documents the unverified boundary |
| `docs/plans/2026-08-19-skill-contract-hardening.md` | Create | This approved implementation plan and progress record |

## Progress

- [x] Task 1 — add structured agent-failure capture and reporting
- [x] Task 2 — remove stale historical wording and enforce evidence language
- [x] Task 3 — close the Gate 2 approval-tool mismatch
- [x] Task 4 — strengthen portability evidence boundaries without false support claims
- [x] Task 5 — run focused, full, and optional behavioral validation

## Approved

Approved by the user on 2026-08-19.

## Tasks

### Task 1: Add structured agent-failure capture and reporting

**Purpose:** The debugging skill handles code and repository failures rigorously while also giving the agent a reproducible protocol for tool loops, context drift, environment mismatch, and policy failures.

**Files:**
- Modify: `.claude/skills/systematic-debugging/SKILL.md` — add a compact failure-capture template before Phase 1, classify agent-specific failure modes, and add a structured final recovery report without weakening the existing root-cause/test-first phases.
- Test: `tools/test_process_router.py` — require the capture fields, agent-failure categories, bounded recovery language, and final evidence/report markers.

**Dependencies:** none

**Implementation notes:** Preserve the current four-phase code-debugging loop. Add fields for task/goal, last successful step, last failed tool or command, observed repetition/context pressure, environment assumptions, and failure class. Require the final report to name failure, root cause, recovery, result, evidence, and follow-up. Keep the skill below 200 lines and avoid duplicating the same rule in more than one new section.

**Rollback:** Revert the skill and its assertions; the current four-phase contract remains intact.

**Preconditions:**
- Run: `python tools/test_process_router.py`
- Expect: exit 0 before the new markers are added.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py`
- Expect: exit 0 with assertions proving all required capture/report fields exist and the skill still has its ordered four-phase procedure.

**Done when:** A reader can use the skill to diagnose both a code failure and an agent-run failure without guessing what state to capture or what the final report must contain.

### Task 2: Remove stale historical wording and enforce evidence language

**Purpose:** Historical measurements remain useful without presenting an unqualified count as a current fact.

**Files:**
- Modify: `.claude/skills/systematic-debugging/SKILL.md` — replace `seven instances so far` with historically qualified wording and point readers to repository evidence rather than an untracked count.
- Modify: `tools/test_process_router.py` — fail if the stale unqualified claim returns; require the replacement to preserve evidence-first language.

**Dependencies:** 1

**Implementation notes:** Do not invent a new count. Use wording such as “historically observed in prior audits” and require current wiring evidence before treating the pattern as present. Keep `ISSUES.md` recording as the durable incident output; do not create a duplicate audit ledger.

**Rollback:** Revert the wording and assertion together.

**Preconditions:**
- Run: `Select-String -Path .claude/skills/systematic-debugging/SKILL.md -Pattern 'seven instances so far'`
- Expect: the current occurrence is found before the task changes it.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py`
- Expect: exit 0 and no unqualified `seven instances so far` claim in the skill.

**Done when:** The skill contains no unsupported current metric and still tells the agent where evidence belongs.

### Task 3: Close the Gate 2 approval-tool mismatch

**Purpose:** The release skill's declared tool contract includes the human approval mechanism it is required to call.

**Files:**
- Modify: `.claude/skills/releasing/SKILL.md` — add `AskUserQuestion` to `allowed-tools` while retaining the explicit Gate 2 wording and no-deploy-without-approval rule.
- Modify: `tools/test_process_router.py` — require `AskUserQuestion` in the parsed `allowed-tools` for `releasing`, alongside the existing exact Gate 2 assertions.

**Dependencies:** none

**Implementation notes:** This is tool availability, not automatic approval. The skill must still call `AskUserQuestion` and must not treat silence or prose as approval. Do not add `Write` or `Edit` to any skill allowlist.

**Rollback:** Remove `AskUserQuestion` from the skill and the corresponding validator assertion.

**Preconditions:**
- Run: `Select-String -Path .claude/skills/releasing/SKILL.md -Pattern '^allowed-tools:','AskUserQuestion'`
- Expect: the approval tool is mentioned in the body but absent from the current allowlist.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py`
- Expect: exit 0 with the Gate 2 tool declared and the exact approval call still present.

**Done when:** The release skill can invoke its required approval tool under the declared skill contract, without pre-approving repository writes or weakening the two-gate policy.

### Task 4: Strengthen portability evidence boundaries without false support claims

**Purpose:** Make the distinction between canonical contract validation and real host conformance explicit and mechanically guarded.

**Files:**
- Modify: `tools/test_portability_contract.py` — require `conformance` for native or verified adapters, require null/explicit unverified status for bridge-required adapters, and assert the test does not claim to execute another host.
- Modify: `tools/test_harness_contract.py` — verify adapter manifest paths exist and preserve the rule that only runtime-verified hosts appear in `native_hosts`.
- Modify: `.claude/portability/capabilities.json` — clarify that bridge-required safety capabilities remain unavailable until host conformance passes, if the current wording is insufficient.
- Test: `tools/test_portability_contract.py` and `tools/test_harness_contract.py` — mutation cases for a falsely verified Codex/generic adapter and a missing adapter path.

**Dependencies:** none

**Implementation notes:** Do not add a fake Codex or generic-agent runner. Do not change either adapter from `bridge-required-unverified` while `conformance` is null. The desired result is an honest refusal boundary plus a test that fails if future edits advertise runtime parity from metadata alone.

**Rollback:** Revert the validator and capability-contract changes; adapter status remains unchanged.

**Preconditions:**
- Run: `python tools/test_portability_contract.py`
- Expect: exit 0 while Codex and generic-agent remain explicitly unverified.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_portability_contract.py; python tools/test_harness_contract.py`
- Expect: both exit 0; mutation fixtures must fail when an unverified adapter is marked native or a declared adapter manifest path is missing.

**Done when:** Static checks prove only honest status transitions, while the repository still clearly states that no non-Claude host has been executed here.

### Task 5: Run focused, full, and optional behavioral validation

**Purpose:** Prove the implementation without confusing inventory, static checks, and live model behavior.

**Files:**
- Test: `.claude/skills/systematic-debugging/SKILL.md`, `.claude/skills/releasing/SKILL.md`, `tools/test_process_router.py`, `tools/test_portability_contract.py`, `tools/test_harness_contract.py` — validation surface only.

**Dependencies:** 1, 2, 3, 4

**Implementation notes:** Run focused checks first, then the full tier. Run `python tools/eval_triggers.py --list` as inventory evidence only. A live trigger run requires explicit cost approval and must report actual model results; it cannot be replaced by the query count. Record any transient full-tier interruption separately from a completed pass.

**Rollback:** No repository rollback; this task only produces command evidence.

**Preconditions:**
- Run: `python tools/parallel_groups.py docs/plans/2026-08-19-skill-contract-hardening.md`
- Expect: exit 0 and a schedulable task order with no undeclared file overlap.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py; python tools/test_portability_contract.py; python tools/test_harness_contract.py; python tools/new_skill_check.py --all; python tools/test_referenced_paths.py`
- Expect: every focused command exits 0.
- Run: `$env:PYTHONIOENCODING='utf-8'; python tools/run_checks.py --tier all --require-test`
- Expect: `PASS: 53 check(s) green` and process exit 0.
- Run: `python tools/eval_triggers.py --list`
- Expect: all 14 skills have query coverage; this remains inventory evidence, not live trigger proof.

**Done when:** All changed contracts are green, the full repository tier completes with exit 0, and the final report separates structural validation from unverified live-host and live-model behavior.

## Constitution gate

- [ ] I Evidence — every task names the exact command and expected output
- [ ] II Test first — every behavior task has a failing contract assertion before implementation
- [ ] III Smallest change — no wholesale ECC copy or unrelated skill rewrite
- [ ] IV Reversibility — no irreversible action; cross-host verification remains gated on actual host availability
- [ ] V No silent degradation — unavailable hosts and unrun live trigger evaluations remain explicitly unverified
- [ ] VI Mechanism — permission, stale-claim, and adapter-status rules are validator-backed
- [ ] VII Secrets — no credentials or external tokens enter the repository

## Complexity tracking

- Article IV exception: Codex/generic-agent conformance cannot be executed from this workspace without those hosts; the plan narrows claims and adds refusal/status guards instead of fabricating conformance.
- Article V exception: live trigger evaluation is optional because it invokes paid model calls; inventory and structural checks are mandatory, while any paid run must be explicitly approved and recorded.

## Open evidence boundary

The first real non-Claude conformance run is deferred until a Codex or generic-agent runtime is available. The implementation must select the host that can execute the bridge contract first, record the host-specific command and receipt, and change only that adapter's status. Until then, both adapters remain `bridge-required-unverified`.

<!-- GATE 1: plan approval. The chain has two; see .claude/workflow.md. -->

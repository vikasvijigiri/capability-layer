---
name: security
description: Run the deterministic security gate and an independent review. Covers authentication, authorization, secrets, external input, dependencies, hooks, deployment, and unsafe agent actions on a high-risk or trust-boundary change. Triggers include "run the security gate", "did we weaken a security control", "is there a secret in this branch", "is this dependency change risky", "security review before shipping", or "residual risk report". Use this whenever a plan or diff hits the high risk tier. Do NOT use to fix findings, exploit live systems, or replace human sign-off — this reports, it does not sign off.
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Security

Formalizes triggering this layer's existing, deterministic security
machinery — built from real, existing usage (`tools/security_gate.py`, the
`security-review` command, `code-review`'s security lens, the
`security-reviewer` agent), not a stub. **This skill does not implement new
security logic** — it is the trigger surface and the procedure for using
what already exists correctly, in order.

## The gate is a fact-checker, not a receipt

The decisions record backing this repository's blast-radius gating and
`tools/security_gate.py`'s own docstring agree: every clause is a fact
about the artefact, computable from two git revisions, never a record that
someone reviewed it. A receipt that can be forged is worse than no
receipt — this repository built and deleted that shape once
(`permission-security/*`'s predecessor `03-review-gate.py`). Do not add a
"security reviewed" flag anywhere; run the gate instead.

## Procedure

1. **Run the deterministic gate first — it's free and it's exhaustive over
   what it checks.**

       python tools/security_gate.py --base <base>

   Five clauses, each a fact: `control-weakened` (a security control lost
   an entry), `secret-in-branch` (a credential anywhere in the branch),
   `sensitive-unmapped` (a sensitive path no test suite maps), `agent-unscoped`
   (an agent that may write with no declared file scope), `dependency-risk`
   (a moved dependency tree `tools/deps.py` rejects). Exit `0` clean · `1` a
   clause fired · `2` a clause could not be evaluated — **`2` is not `0`**.
2. **A `1` or `2` exit is the finding — do not re-derive it by reading the
   diff yourself first.** The gate already computed it; reading the diff is
   for understanding *why*, not for discovering *whether*.
3. **For everything the gate doesn't compute** (authentication logic,
   authorization boundaries, external-input handling, data exposure,
   deployment configuration, unsafe agent actions in the *behavior* sense
   rather than the scope-declaration sense) — invoke `code-review` with its
   security lens (`.claude/skills/code-review/references/security-review.md`)
   and, when subagents are available, dispatch `security-reviewer`.
4. **Licence and SBOM**, when dependencies changed:

       python tools/deps.py --sbom

   A denied licence exits 1; one that could not be read exits 2.
5. **Report prioritized findings, evidence, remediation, and residual
   risk.** Do not exploit live systems, retrieve real secrets, edit files,
   or sign off — this stage reports; a human or Gate 2 signs off.

## When this is mandatory, not optional

`tools/scope.py`'s risk tier already forces `high` for a sensitive surface
(auth, credentials, the installer, packaging) on its own — see
`.claude/workflow.md`'s risk-tier table. A plan or diff at that tier gets
this skill's full procedure, not a skim. `code-review`'s security lens
being "computed rather than judged" (per the same decision) is what makes
it mandatory at that tier rather than a judgment call.

## Red Flags

- "The gate passed, so we're secure." The gate covers 5 specific clauses,
  not the whole surface — step 3's review still runs.
- Re-reading the diff by eye to confirm what `security_gate.py` already
  computed, instead of trusting `1`/`2` as the finding.
- Recording a "reviewed" flag anywhere instead of re-running the gate next
  time — the gate must stay re-runnable and stateless, per the receipt
  history above.
- Fixing a finding inside this skill. That's a handoff to `implementation`
  or `debugging`, not this skill absorbing another job.

## Next step

Hand prioritized findings to the caller (`task-analysis` if found during
planning, `code-review`/`release-git` if found before delivery/shipment).
A clean gate plus a clean review is evidence for Gate 2, not an
auto-approval of it.

## Routing

- Mandatory validator: `python tools/security_gate.py --base <base>` — the
  only required check this skill owns; everything else is read-only review.
- Dispatches `security-reviewer` and `code-review`'s security lens; neither
  is a handoff, both return here.
- Entered from `task-analysis` (Stage A/C, a sensitive surface), from
  `code-review` (its own security lens flags something needing the full
  gate), or directly when the user asks.
- Terminal handoff: back to the caller with findings; never signs off
  itself.
- Vetted external references (OWASP CheatSheets/ASVS/WSTG, SAST tooling):
  `.claude/rules/security-resources.md` (path-scoped; pointer only).

## Success

The deterministic gate ran and its exit code is quoted, every applicable
clause was resolved rather than left `unknown`, the broader review covered
what the gate does not compute, and residual risk is named rather than
implied clean.

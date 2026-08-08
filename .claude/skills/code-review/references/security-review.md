---
name: security-review
description: Independent security review of changes touching authentication, authorization, secrets, personal data, external input, dependencies, deployment or trust boundaries. Triggers include "threat model this", "security review", "check auth", "audit dependencies". Do NOT use as generic code review, for formatting, or to fix findings while reviewing.
when_to_use: when a change crosses a security or trust boundary
effort: high
model: opus
disable-model-invocation: true
---

# Security Review

Evaluate security risk independently from correctness review. Produce findings
that are specific enough to fix and evidence that is specific enough to verify.

## Procedure

1. Define the assets, actors, trust boundaries, entry points, privileged
   operations, sensitive data, and deployment surfaces in scope.
2. Read the relevant diff, configuration, tests, dependency manifests, and
   existing security conventions. Do not infer protection from a passing suite.
3. Check authentication, authorization, input validation, output encoding,
   secret handling, logging, privacy, dependency exposure, unsafe defaults,
   injection paths, and failure behavior.
4. Write abuse cases for the highest-risk paths and identify the control that
   prevents each one. Mark controls as evidenced, missing, or unverified.
5. Rank findings by exploitability and impact. Each finding must include
   `file:line`, attack precondition, consequence, evidence, and a concrete fix
   direction. Record accepted residual risk separately.
6. Define verification for each finding: test, static check, dependency check,
   configuration assertion, or operational control.

## Boundaries

- Do not edit the change while reviewing it.
- Do not call a change secure because no issue was found; state what was and was
  not assessed.
- Do not substitute secret scanning for threat modeling or dependency scanning.
- Route actionable findings to `task-brief`; keep this review independent.

## Routing

For high-risk or cross-boundary changes, dispatch `security-reviewer` for an
independent read-only pass. This skill owns triage and routing; the agent does
not fix findings or provide sign-off.

- Entered from any stage when a trust boundary or security-sensitive asset is
  involved; recommended before `writing-plans` approval and before `code-review`.
- Terminal handoff: the requesting stage, or `task-brief` when remediation is
  required.

## Success

The report names the threat surface, evidence, ranked findings, residual risk,
and a verification method for every material control.

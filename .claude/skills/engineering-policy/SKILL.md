---
name: engineering-policy
model: opus
description: Universal engineering standards and hard safety limits — SOLID/DRY/KISS/YAGNI, clean architecture, naming, dependency governance, secrets handling, context economy, Definition of Done. Read for "best practice", "engineering standards", "code standards", "policy check", "architecture rules", "is this good code", "should I add package/lib", "over-engineered", "definition of done", before writing non-trivial code, and before declaring any task complete. Cites core policy rules. Prefer this over recalling a rule from memory - it cites the actual policy text rather than a paraphrase. Do NOT expect step-by-step process — that is workflow-orchestrator.
effort: high
argument-hint: "[optional topic to cite, e.g. naming or secrets]"
user-invocable: true
---

# Engineering Policy

Universal standards and standing rules. Policy is declarative — it defines what is allowed, required, or forbidden, independent of execution steps.

## Core Software Principles

- **SOLID**: Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion. Apply proportionally (do not add interfaces for simple 5-line fixes).
- **DRY**: Do not duplicate logic, but do not extract premature abstractions for two merely similar call sites. Three repetitions before abstracting.
- **KISS**: Simplest working solution that solves the actual requirement.
- **YAGNI**: Build strictly for current requirements. No speculative configuration, flags, or future extension points.
- **Clean Architecture**: Respect existing layer boundaries and dependency direction. Match codebase conventions over generic external patterns.
- **Cohesion & Coupling**: High cohesion within modules, low coupling across modules. Changes must not ripple into unrelated subsystems.
- **Explicit Naming & Comments**: Code names explain *what* a component does; comments explain non-obvious *why* (invariants, workarounds, constraints).
- **Secure Defaults**: Validate at external trust boundaries. Never commit, log, or echo credentials, secrets, or tokens.

## Dependency & Resource Governance

- **Zero-Cost & Open-Weight Default**: Default to free-tier cloud services, free APIs, and open-weight models (`openai/gpt-oss-120b` on Groq for LLM calls). Request explicit user approval before using paid options unless specified by the user.
- **Dependency Minimization**: Use stdlib first, then existing dependencies. Only add a new dependency if neither suffices, recording a 1-line justification in the commit/PR body.

## Definition of Done (Floor Quality Gate)

Every task completion must satisfy:
1. Builds, lints, and tests pass (existing tests updated).
2. Acceptance criteria in task brief are satisfied.
3. Code touched has been reviewed (`code-review`).
4. Docs updated if API/architecture changed.

## Git & History Policy

- **Atomic Commits**: Small, single-purpose, reversible commits.
- **Commit Messages**: State *why* the change was made (diff shows *what*).
- **History Preservation**: Never rewrite published history (`git push --force`, amending pushed commits) without explicit user consent.
- **ZERO AI Attribution**: NEVER include AI/agent signatures, "Co-Authored-By: Claude", or bot emojis in git history.

## Context & Output Economy

- **Lazy Loading**: Read files only when required for current task execution. Never preload whole repos or unrelated folders.
- **Concise Outputs**: Omit preambles, restatements of asks, and self-narration. Output high-signal code, tables, and verifiable evidence.
- **Verifiable Evidence**: Never omit exact command output, failing test details, or unverified assumptions.

## Non-Negotiable Safety Guards

- NEVER push, merge, publish a PR, or deploy without explicit user approval.
- NEVER commit secrets or credentials.
- NEVER report unverified checks as passed.
- NEVER weaken or delete tests to make builds green.

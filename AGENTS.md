# Universal agent operating contract

This file is the harness-neutral entry point for any coding agent working in
this repository. A harness may add its own adapter instructions, but it must
preserve these invariants.

## Before acting

1. Read this file and `TASK.md` when present.
2. Read the relevant design, specification, plan, and acceptance evidence.
3. Inspect the repository's existing conventions before inventing new ones.
4. State assumptions when requirements are incomplete.

## SDLC contract

Use the smallest applicable path:

```text
brief → design → plan → implement → verify → clean → review → deliver → release → record
```

Do not skip verification for a completion claim. Do not push, merge, publish,
deploy, or spend money without explicit approval. Keep changes within scope,
preserve user changes, and report failures as failures.

## Capability adapters

`.claude/` is the only repository-native source of truth for skills, agents,
commands, workflows, rules, hooks, settings, output styles, memory, and
workflow state. Every host must follow the complete path map in
`harnesses.json`. Claude Code consumes `.claude/` natively; Codex,
Gemini, VS Code, and other hosts must read or project from `.claude/` without
creating a second, untracked source of truth.

No generated adapter directory is required. Hosts must consume or project the
canonical `.claude/` content directly.

Hosts that cannot auto-discover Claude lifecycle hooks must invoke the canonical
checks under `.claude/hooks/` through their own lifecycle API. A null or absent
native hook registration must not be interpreted as an absent hook contract.

## Runtime model

The normal execution model is host-managed. Claude Code, Codex, Gemini, or a
VS Code agent extension provides the model session and operates under this
repository contract. No `ANTHROPIC_API_KEY` is required for that path. The
repository runner's `--host-managed` mode creates the handoff and evidence
contract; it does not impersonate the IDE host. Its `--dry-run` mode validates
the contract offline. Its optional `--sdk-live` mode is only for standalone
automation and is not required for IDE use.

## Evidence contract

Every important claim needs evidence appropriate to the claim: test output for
behavior, a diff for scope, rendered output for visual quality, and a smoke or
log result for deployment. Record unresolved risks, deliberate exceptions,
owner, and follow-up date.

## Failure and safety

Stop on secrets, destructive ambiguity, scope escape, failed required checks,
or a missing approval. Use repository-native diagnosis and preserve recovery
state. Never hide an error to make a gate green.

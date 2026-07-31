---
name: deployment-secrets-provisioning
model: haiku
description: Splits required deployment secrets into auto-generatable vs. must-supply-by-human, and provisions them into the target platform's secret store. Use for "set up secrets for deploy", "what env vars do I need to provide", "provision API keys", "secrets for this environment", "what keys do I need to provide", "set up the env vars", "where do the secrets go", "it needs an API key to run". Prefer this over pasting values into a dashboard - the generatable vs must-supply split is what stops a deploy stalling halfway. Do NOT use to store or print an actual secret value in chat/logs. One step of a release; for an end-to-end deploy with secrets, health checks and live-URL verification, use `deployment-pilot`.
effort: low
---

# Secrets Provisioning Skill

Splits `required_secrets` into generatable-by-us vs. must-supply-by-human, and produces the platform-specific provisioning steps.

## When to use
- "set up secrets for deploy", "what do I need to provide", "provision API keys"

## Steps
1. Classify each entry in `required_secrets` as generatable (random tokens, internal keys) or must-supply (third-party API keys).
2. Produce `target_platform`-specific commands/console steps to set each.
3. Return the `secrets_plan` — never the actual secret values.

## Notes
Never echo, log, or commit an actual secret value — this skill only ever names what's needed and where it goes.

## Routing

**Validator (required): `.claude/validators/deployment-smoke-test.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/deployment-canary.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/deployment-pipeline.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

## Human gate

Gate before writing any secret to a provider, and name in the brief which values the user must supply versus which are generated. A secret written to the wrong environment is not reversible by deleting it -- treat it as rotated-and-burned, and say that in the undo line rather than claiming it is reversible.

Never print secret values into the dialogue. Name the key, never the value.

Invoke `approval-brief` and let it run the `AskUserQuestion` dialogue. Do not write your own prose "shall I proceed?" -- the dialogue shape, the option wording and the no-bundling rule live in that one skill so they cannot drift apart here.

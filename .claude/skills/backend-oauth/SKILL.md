---
name: backend-oauth
model: sonnet
description: Generates OAuth provider configuration and integration-test scaffolding for an API. Use for "set up OAuth", "add Google/GitHub login", "configure OAuth client", "OAuth redirect URI", "auth provider integration", "let people sign in with google", "social login", "add sign in with github", "users shouldn't need a password". Prefer this over rolling your own provider integration - redirect URIs and client config are where it silently breaks. Do NOT use for session/cookie-based auth with no OAuth provider involved. Implementation-level; for choosing the stack, database or architecture pattern in the first place, use `stack-selector`.
effort: medium
---

# OAuth Skill

Encapsulates steps to configure and validate an OAuth provider for an API. Pure generator — no live side effects.

## When to use
- "set up OAuth", "add login with Google/GitHub", "configure an OAuth client", "redirect URI setup"

## Steps
1. Validate `provider` is supported.
2. Generate config artifacts (env vars, sample redirect URI).
3. Produce a sample integration test script.
4. Return `config_snippet` + `test_instructions`.

## Notes
Side-effects (actually registering the app, storing secrets) belong to the workflow wrapping this skill, with validators and a human approval gate — never performed here directly.

## Routing

**Validator (required): `.claude/validators/backend-oauth.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/backend-oauth.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/backend-oauth.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.

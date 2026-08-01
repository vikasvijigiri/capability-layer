# Capability Routing

Single source of truth for capability routing. Replaces the nine
`.claude/capabilities/<domain>/index.md` files, removed on 2026-07-31.

Three consumers parse this file, so its structure is load-bearing:

- `.claude/hooks/pre-run/02-capability-router.py` — reads each `## <domain>`
  heading and the `Keywords:` line under it, matches the prompt, and injects the
  result into the turn.
- `tools/generate_registry.py` — takes the set of `## <domain>` headings as the
  authoritative capability list, and files a skill under a capability when its
  `<domain>-` name prefix matches one.
- `tools/resolve_capability.py` — same scan, for manual queries.

**Format contract.** One `## <domain>` heading per capability, lowercase, matching
the skills' name prefix exactly. Exactly one `Keywords:` line per domain, comma
separated. Add a domain by adding a section; nothing else needs editing.

**Scope.** This file routes only the 54 `<domain>-` prefixed capability skills,
because a match here resolves to a *name prefix*, not a skill. The 31 unprefixed
process skills (`brainstormer`, `code-review`, `error-recovery`, …) are routed by
`.claude/routing/process-skills.md` and `05-process-skill-router.py`, which name
skills directly. Do not add a process-skill keyword here — it would emit a
`<domain>-` prefix that matches nothing.

Skill-level routing — which validator is mandatory, which blueprint takes
precedence, which workflow orchestrates the multi-step case — lives in each
skill's own `## Routing` section, not here. That was duplicated in both places
until 2026-07-31; two copies of a routing rule means the stale one eventually
wins.

---

## ai

Purpose: AI-specific work — prompt engineering, RAG, embeddings, evaluation,
model routing, structured output, moderation, sub-agent orchestration.

Keywords: ai, rag, embeddings, hallucination, evaluation, model-routing, llm, prompt, chatbot, genai, vector search, semantic search, retrieval, fine-tune, agent, gpt, token limit, context window, classification, sentiment, summarize, tldr, json mode, structured output, moderation, content policy, sub-agents, multi-agent, orchestration

Artefacts:
- `.claude/blueprints/` — `ai-rag`
- `.claude/validators/` — `ai-hallucination-check`, `ai-output`
- `.claude/workflows/` — `ai-rag`

## backend

Purpose: backend engineering — APIs, databases, infra-as-code, observability,
performance.

Keywords: backend, api, database, infra, oauth, observability, server, endpoint, db, sql, migration, auth, login, service, queue, job, cron, slow query, schema, rest, graphql, microservice, rate limit, throttle, 429, background job, async job, cache, caching, invalidate cache, idempotency

Artefacts:
- `.claude/blueprints/` — `backend-oauth`
- `.claude/validators/` — `backend-change`, `backend-oauth`
- `.claude/workflows/` — `backend-oauth`
- `.claude/playbooks/` — `backend-oauth`
- `.claude/templates/` — `backend-api`

## debugging

Purpose: diagnostics — reproducing bugs, correlating logs, profiling, root-cause
analysis.

Keywords: debugging, rca, logs, repro, profiler, bug, error, crash, broken, not working, exception, stack trace, why is this failing, weird behavior, root cause, memory leak, heap growing, oom, flaky test, intermittent failure, fails in ci, traceback, stacktrace, failing, failure, hangs, deadlock, segfault, panic, regression, silently, no output

Artefacts:
- `.claude/blueprints/` — `debugging-rca`
- `.claude/validators/` — `debugging-hotfix`
- `.claude/workflows/` — `debugging-repro`

## deployment

Purpose: deployments, infrastructure-as-code, release orchestration, rollback.

Keywords: deployment, infra, ci, cd, canary, provisioning, deploy, host, publish, ship it, put online, release, rollout, pipeline, github actions, docker, live url, secrets, env vars, api keys, health check, readiness probe, liveness probe

Artefacts:
- `.claude/blueprints/` — `deployment-canary`
- `.claude/validators/` — `deployment-smoke-test`
- `.claude/workflows/` — `deployment-pipeline`

## documentation

Purpose: authoring, maintaining and validating repository documentation.

Keywords: documentation, docs, api, style, link-checks, readme, explain this repo, write docs, comment this, onboarding doc, changelog, doc this, release notes, adr, decision record, why did we choose

Artefacts:
- `.claude/blueprints/` — `documentation-structure`
- `.claude/validators/` — `documentation-link-check`
- `.claude/workflows/` — `documentation-release`

## frontend

Purpose: UI, UX, accessibility, component libraries, bundling, client-side
observability.

Keywords: frontend, ui, ux, accessibility, components, visual-testing, page, layout, css, styling, button, responsive, looks broken, design, screen, component, react, a11y, visual regression, screenshot diff, mobile, breakpoint, viewport, form, input, validation, user flow, journey, navigation, nav, wireframe, state management, client state, prop drilling, loading state, empty state, error state, re-render, figma, design token, modal, dropdown

Artefacts:
- `.claude/blueprints/` — `frontend-component`
- `.claude/validators/` — `frontend-visual-diff`
- `.claude/workflows/` — `frontend-release`

Order note: `design-system` gates this capability. It owns `DESIGN.md`, the token
table every `frontend-` skill generates and checks against, and it is an
unprefixed process skill, so a `frontend-` prefix scan will not surface it —
`process-skills.md` routes it by name instead. For a
new feature: `frontend-ux-flow` → `design-system` (if no `DESIGN.md`) →
`frontend-state-architecture` → `frontend-component-generator` /
`frontend-form-builder` → the audit skills.

## research

Purpose: research and discovery — papers, competitive analysis, benchmarks,
sourcing and citation.

Keywords: research, papers, literature-review, citation, evidence, look into, investigate, compare options, what's the best way, find out, survey, benchmark, competitive analysis, versus, which is faster, which is cheaper

Artefacts:
- `.claude/validators/` — `research-citation-check`

## security

Purpose: adversarial review and hardening — injection, secrets exposure,
authorization, dependency risk.

Keywords: security, vulnerability, injection, sql injection, xss, secrets, exposed credentials, authz, authorization, auth bypass, dependency vuln, cve, exploit, is this safe, security review, penetration, owasp

Artefacts:
- `.claude/validators/` — `security-secrets-scan`

## testing

Purpose: automated test authoring and execution — unit, integration,
end-to-end, mutation, load.

Keywords: testing, test, unit test, integration test, e2e, end-to-end, playwright, mutation testing, test coverage, write tests, add tests, run the tests, test this, coverage is thin, browser test, regression suite, pytest, jest, vitest, assertion, fixture, mock, test suite, failing test, coverage

Artefacts:
- `.claude/validators/` — `testing-coverage-gate`

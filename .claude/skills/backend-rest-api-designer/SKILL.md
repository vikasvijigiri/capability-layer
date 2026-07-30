---
name: backend-rest-api-designer
model: opus
description: Designs a REST API surface (routes, methods, status codes, pagination, error shape) before implementation begins. Use for "design this API", "what routes do we need", "REST endpoint design", "API contract", "pagination scheme", "what should the endpoints look like", "design the api", "how should the frontend talk to this", "we need an api for this". Prefer this over inventing routes while implementing - an unplanned API surface becomes a permanent contract. Do NOT use once implementation has already started against an agreed contract — that's backend-engineer's job. Implementation-level; for choosing the stack, database or architecture pattern in the first place, use `stack-selector`.
---

# REST API Designer Skill

Produces a route table (method, path, request/response shape, status codes, pagination, error envelope) from a resource model and use cases.

## When to use
- "design this API", "what routes do we need", "REST endpoint design", "API contract"

## Steps
1. Enumerate resources and their relationships from `resource_model`.
2. Map `use_cases` to CRUD/custom routes with methods and status codes.
3. Define a consistent pagination scheme and error envelope.
4. Return the route table as the frozen `api_contract`.

## Notes
Freeze the contract before implementation starts — changing it mid-build is a scope change, not a bug fix.

## Routing

**Validator (required): `.claude/validators/backend-change.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/backend-oauth.md` - a matching blueprint takes precedence over a hand-built solution.

---
name: ai-structured-output
model: sonnet
description: Forces a model response into a strict JSON schema (or other structured format) and validates it before returning. Use for "make this return JSON", "enforce a schema on the output", "structured output", "parse this into a typed object", "it keeps replying in prose", "I need the same fields every time", "parse the reply into an object", "make the output predictable". Prefer this over regex-parsing a model reply - schema validation fails loudly instead of silently. Do NOT use for free-form prose responses with no schema to enforce. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
---

# Structured Output Skill

Generates a response constrained to `json_schema` and validates it before returning, retrying once on schema-validation failure.

## When to use
- "return this as JSON", "enforce a schema", "structured output", "typed response"

## Steps
1. Generate a response for `prompt` constrained to `json_schema`.
2. Validate the output against the schema.
3. On failure, retry once with the validation error appended to the prompt.
4. Return the validated structured object.

## Notes
Never hand back output that fails schema validation — retry once, then surface the failure explicitly rather than returning malformed data.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.

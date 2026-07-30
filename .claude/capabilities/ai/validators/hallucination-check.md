> **Superseded.** The canonical copy of this file is `.claude/validators/ai-hallucination-check.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Hallucination Check — ai/validators/hallucination-check.md

Purpose: lightweight validator to detect unsupported assertions and missing citations.

Checks

- Named entities referenced should have at least one supporting snippet.
- Assertions of fact must be traceable to evidence snippets.
- If confidence below threshold, mark for human review.

Failure handling

- Mark output as `needs_review` and attach evidence.
- Optionally, trigger follow-up retrieval for more evidence.
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "hallucination-check", "capability": "ai"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the output is persisted as an artifact.

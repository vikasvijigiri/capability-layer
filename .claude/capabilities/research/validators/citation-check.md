> **Superseded.** The canonical copy of this file is `.claude/validators/research-citation-check.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Citation Check Validator — research/validators/citation-check.md

Purpose: verify that research outputs are traceable to credible, real sources.

Checks

- Every factual claim has an attached source URL or citation
- Sources are not fabricated (spot-check via `web-search`/`papers-extraction`)
- Competitive/benchmark comparisons cite the dataset or benchmark used, not estimates

Failure handling

- Mark output as `needs_review` and list unsupported claims
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "citation-check", "capability": "research"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the findings are persisted as a report.

Usage

Required gate for `web-search`, `papers-extraction`, `citation-scoring`,
`competitive-analysis`, `benchmark-comparison` before their output is treated as final.

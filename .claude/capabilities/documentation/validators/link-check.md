> **Superseded.** The canonical copy of this file is `.claude/validators/documentation-link-check.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Link Check Validator — documentation/validators/link-check.md

Purpose: ensure internal and external links in documentation resolve.

Checks

- No 404s for internal links
- External links return 200 or are flagged

Failure handling

- Mark PR as `needs_fix`
- Provide report with broken links
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "link-check", "capability": "documentation"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` for any generated doc/changelog/ADR artifact.

Usage

Include in `doc-release`, and as the gate for `doc-generator`, `api-extractor`, `changelog-generator`, `adr-writer`.

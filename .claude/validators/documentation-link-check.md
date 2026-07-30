# Link Check Validator — .claude/validators/documentation-link-check.md

Purpose: ensure internal and external links in documentation resolve.

Checks

- No 404s for internal links
- External links return 200 or are flagged

Failure handling

- Mark PR as `needs_fix`
- Provide report with broken links
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "documentation-link-check", "capability": "documentation"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` for any generated doc/changelog/ADR artifact.

Usage

Include in `.claude/workflows/documentation-release.md`, and as the gate for `doc-generator`, `api-extractor`, `changelog-generator`, `adr-writer`.

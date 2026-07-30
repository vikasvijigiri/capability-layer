> **Superseded.** The canonical copy of this file is `.claude/validators/frontend-visual-diff.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Visual Diff Validator — frontend/validators/visual-diff.md

Purpose: compare component or page screenshots against baseline.

Checks

- Pixel/threshold differences
- Significant layout shifts

Failure handling

- Mark change as `requires_approval` if above threshold
- Provide diff image and coordinate-based summary
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "visual-diff", "capability": "frontend"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` for any promoted component/blueprint.

Usage

Run this validator in `release-workflow` before promotion, and as the gate for `visual-regression`, `responsive-audit`, `accessibility-check`, `component-generator`, `bundling-helper`.

---
description: Review a GitHub pull request with independent bug, policy, security, and history checks; print findings by default and require confirmation before commenting.
---

# Pull Request Review

Mode: read-only
Arguments: `$ARGUMENTS` identifies the PR; `--comment` requests a proposed comment flow.

Inspect the PR state, diff, repository instructions, and relevant history. Run
independent review lenses, validate each finding before reporting it, and output
only high-confidence findings with file and line evidence. Default output is
local. If `--comment` is supplied, show the complete proposed comment and ask
`AskUserQuestion` before posting anything. Never merge, push, or close
the PR.

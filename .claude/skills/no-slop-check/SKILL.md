---
name: no-slop-check
model: sonnet
description: Runs the No-Slop Checklist (checklist.md) line-by-line over every source file, reporting unused scaffolding, speculative abstraction and placeholder comments with file:line references. Use for "check for slop", "dead code", "stale code", "unused files", "nobody imports this", "leftover junk", "clean this up", "tidy the repo", and before shipping, finalizing or handing over a repo. Prefer this over eyeballing the tree yourself — it catches the AI-authored residue a quick scan reliably misses. Do NOT use for logic bugs — that is code-review.
user-invocable: true
argument-hint: "[path or glob to sweep, default: whole repo]"
effort: high
context:
  - checklist.md
allowed-tools:
  - Read
  - Grep
  - Glob
provides: [quality-sweep]
requires: []
produces_artifact: false
retryable: true
---

# /no-slop-check — dead/stale code and quality gate

Global — works in whatever repo it's invoked in. Runs
[`checklist.md`](checklist.md) (the No-Slop Checklist) against every
coding/source file in that repo, regardless of language.

**Default scope is the whole repo, not a subset** — every source/code file
in whatever languages the repo actually uses, excluding:
- Noise directories: `.git/`, dependency directories (`node_modules/`,
  `__pycache__/`, `.venv/`, `vendor/`, etc.), build/output directories,
  editor/tool caches (`.ipynb_checkpoints/` and similar)
- Vendored/third-party files not authored in this repo (a bundled library,
  a class file from an external package, generated bindings) — judging
  someone else's code against this checklist doesn't make sense, it's not
  this repo's to fix
- Generated build artifacts (compiled binaries, `.log`/`.aux`/`.out`
  style build output, lockfiles)

If the user names a specific file or narrower scope, check only that —
don't re-scan the whole repo every time it's invoked for a targeted ask.

## Steps

1. **Read `checklist.md`** for the exact 10 categories and their items —
   don't restate them from memory, they may have been edited.
2. **Enumerate every target file** per the scope above. Notebooks count
   too — check code cells, skip large output blobs. If a file's format
   makes an exhaustive read impractical (a huge generated/binary-heavy
   notebook, a compiled cache format), say so explicitly rather than
   silently skipping or pretending to have reviewed it — see checklist
   item 10.
3. **Go through each file explicitly, line by line** — read the whole
   file, not a sample or a skim for obvious patterns. Check every
   checklist category that applies to code (categories 5 "Untested edges"
   and 8 "Scope" are about a specific task's brief, not a general codebase
   sweep — skip those two here; the other eight apply directly regardless
   of language: dead/commented-out blocks, duplication, naming, stale
   comments, and consistency aren't Python-specific). Record findings with
   `file:line`.
4. **Prioritize dead/stale code** (Category 1) in the report when it's
   present — it's usually the highest-value, most-actionable category.
   Don't bury it under lower-value nitpicks.
5. **Report, organized by category**, most-actionable first:
   - Dead code (imports, functions, unreachable branches, "just in case"
     additions)
   - Unhandled errors (missing/broken imports treated as if they'd work,
     swallowed exceptions)
   - Duplication
   - Naming
   - Comments (stale or restating-the-obvious)
   - Consistency with the rest of the codebase
   - Fake done (stubs, hardcoded placeholder returns, leftover debug prints)
   - Verified vs. claimed (only relevant if reporting on code someone
     claimed was working/tested — flag if that claim can't be confirmed by
     actually running it)
6. **Fix-or-justify, not silent-pass.** For each finding: either it's a
   real hit (report file:line + one-line description of what's wrong), or
   it's a deliberate, justified exception (note why in one line) — per the
   checklist's own rule. Don't just list line numbers with no explanation.
7. **Don't fix anything automatically.** This skill reports; it doesn't
   edit. Fixing findings is a separate, explicit follow-up the user
   approves per file/finding.

## Note on project-local overrides

A repo can have its own `.claude/skills/no-slop-check/` with a
repo-tailored version of this skill (e.g. narrower default scope, repo-
specific framing). Where both exist, the project-local one is expected to
take precedence for that repo — this global version is the default for
any repo that doesn't have its own.

---
name: code-review
model: opus
description: Independent Staff Engineer review of a pending git diff — requirements fit, correctness, architecture, maintainability, security, performance, naming, test coverage. Use for "review this", "check my code", "is this ready", "can I ship this", "code quality check", "audit diff", "find bugs in diff", "pre-commit check", before every commit, push, PR or release, and when asked about pending or recent changes. Prefer this over your own read of the diff - an independent pass is the entire value, and it is the step time pressure deletes first. Do NOT use for typos or single-line fixes.
effort: high
argument-hint: "[optional focus, e.g. security or a path]"
user-invocable: true
allowed-tools:
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git branch:*)
  - Bash(npm run:*)
  - Bash(yarn:*)
  - Bash(pnpm:*)
  - Bash(pytest:*)
  - Bash(go test:*)
  - Bash(go build:*)
  - Bash(go vet:*)
  - Read
  - Grep
  - AskUserQuestion
  - Skill
provides: [review]
requires: [implementation]
produces_artifact: false
retryable: true
---

# /code-review — Independent Diff Review

Independent audit of pending git diffs against `engineering-policy` standards. Focus strictly on changed lines and their direct context.

## Review Steps

### 1. Gather Diff State
- Inspect `git status --porcelain`, `git diff --cached` (staged), and `git diff` (unstaged).
- Check current branch (`git branch --show-current`). If empty diff, stop.

### 2. Audit Core Dimensions
- **Requirements Fit**: Verify change fulfills acceptance criteria without scope creep or missing requirements.
- **Correctness**: Audit for logic bugs, unhandled nulls/exceptions, off-by-one errors, and broken contracts.
- **Architecture**: Enforce layer boundaries, existing conventions, and `decisions/` ADR alignment.
- **Maintainability & Slop**: Check for dead code, duplicate logic, misleading comments, and inconsistent formatting.
- **Security**: Audit boundary validation, secrets exposure, and env var consistency (`.env.example`).
- **Performance**: Flag non-trivial computational or query bottlenecks.
- **Test Coverage**: Ensure meaningful test verification for changed functionality.

### 3. Verification Execution
- Run existing project build/lint/test commands (`npm test`, `pytest`, etc.). Never invent fake test passes. Report unverified items explicitly.

### 4. Verdict & Receipt
- **Reject**: If any blocking defect exists. State exact fix requirements.
- **Pass**: Run review gate receipt recorder:
  ```bash
  python ".claude/hooks/pre-commit/03-review-gate.py" --record
  ```

### 5. Draft Commit / PR Message
- Match existing repo commit style (`git log -n 5`). Draft commit/PR message. Do not run `git commit` or `git push` directly.

## Human gate

**This skill never runs `git commit`, `git push` or `git merge`, and never opens a PR.** It reviews and it drafts the message; the act itself is a separate, gated decision.

When a Pass verdict is followed by an actual commit, push, merge or PR, gate that act first. One gate per act: a yes to committing is not a yes to pushing.

Invoke `approval-brief` and let it run the `AskUserQuestion` dialogue. Do not write your own prose "shall I proceed?" -- the dialogue shape, the option wording and the no-bundling rule live in that one skill so they cannot drift apart here.

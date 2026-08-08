---
name: delivering
description: Land reviewed work in the repository - branch, PR, merge queue. Triggers include "open a PR", "push this up", "merge it", "ship it", "is this ready to land", "rebase onto main", "resolve these conflicts", "why is the merge queue stuck". Do NOT use to deploy or roll out (releasing), to review code (code-review), or to diagnose a failing check. Use this whenever reviewed work must reach the repository.
when_to_use: when verified reviewed work is ready for repository integration
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# Delivering

Prepare the reviewed change for safe repository integration. This stage may
create local commits, branch/PR metadata, and a merge-queue handoff according
to the host contract. It does not deploy. Shipment approval remains the second
and final human gate.

<HARD-GATE>
Never integrate a change without current verification evidence, a passing
automated code review, clean secret checks, and a named base branch. Never use
model preference to choose between competing changes: promote the candidate
with objective checks, acceptance coverage, security status, scope fit,
rollback, and then the smallest lower-risk diff.
</HARD-GATE>

## Steps

1. Confirm the worktree/branch is isolated and the base is known. For parallel
   work, use one worktree per task and serialize shared-interface changes.
2. Run the repository's required all-tier checks and secret scan on the actual
   candidate. Preserve command, exit code, and relevant output as evidence.
3. Rebase or merge the latest base. If conflicts occur, classify them. Resolve
   only mechanical, non-security conflicts with bounded attempts; otherwise
   return a structured conflict incident to `systematic-debugging`.
4. Prepare the PR or merge-queue handoff. Do not bypass protected-branch rules,
   required checks, or merge queue. Do not deploy.
5. Return `clean`, `conflict`, or `blocked` with changed paths, base, checks,
   conflict files, and evidence.

## Recovery

Conflict recovery is limited to two attempts. A failed required check returns to
the failed stage, not to a blind full rerun. Scope drift, security findings, or
repeated conflicts return to the plan gate.

## Next step

On a clean handoff, invoke `releasing` for release readiness and the shipment
approval gate. On conflict or failed checks, invoke `systematic-debugging`.

## Routing

- Mandatory validator: all-tier checks, secret scan, review receipt, and base-branch evidence.
- Terminal handoff: `releasing` on clean; `systematic-debugging` on failure.
- No separate delivery approval exists; shipment approval is owned by `releasing`.

## Success

The candidate is reproducible, review-backed, conflict-safe, and queued for
integration without silently pushing, merging, or deploying around policy.

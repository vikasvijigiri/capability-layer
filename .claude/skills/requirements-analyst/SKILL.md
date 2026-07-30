---
name: requirements-analyst
model: opus
description: Turns a goal/objectives/deliverables statement into a PRD, an MVP-cut feature list, and testable acceptance criteria per feature. Owns the Scope-Cut Defaults for resolving ambiguous requirements without asking. Use whenever a vague ask needs to become a concrete spec, when the user says "I need a PRD", "write a PRD", "what should we build", "define the requirements", "scope this", "what are the acceptance criteria", and always before any architecture or stack decision. Prefer this over inferring requirements while coding — undefined requirements cannot be judged complete. Do NOT use once a PRD already exists and only implementation remains.
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
provides: [prd, acceptance-criteria, scope-cut]
requires: [goal]
produces_artifact: false
retryable: true
---

# Requirements Analyst

Turns a goal statement into something the rest of a build can act on: a PRD, a feature
list already cut to MVP scope, and one or more concrete acceptance criteria per
feature. Reusable standalone — any "here's a vague idea, make it a spec" request, not
just inside `mvp-builder`.

## Steps

1. **Restate the goal, objectives, target users, constraints, and deliverables** as
   given — don't infer a deliverable that wasn't named.
2. **Draft the feature list**, each item with one or more concrete, checkable acceptance
   criteria (a criterion is something `deployment-pilot`'s QA phase can actually verify
   against the live product — "user can create an account and log back in," not "auth
   works well").
3. **Apply the Scope-Cut Defaults** to anything ambiguous — never to something the goal
   explicitly named:
   - Read-only over read-write, where the goal didn't specify which.
   - Single-user over multi-user/multi-tenant, where the goal didn't specify.
   - Synchronous over async/queued processing, where the goal didn't specify.
   - One happy path over broad edge-case coverage for a first cut.
   - Seed/fixture data over a full admin CRUD UI, where the goal only needed the data to
     exist, not to be managed through a UI.
   - Every cut gets one line in the PRD's "Cut for v1" list — cuts are recorded, never
     silent.
4. **Flag feature-flag candidates.** A feature only needs flag-gating (ship hidden,
   enable later) if it touches auth, payments, or an irreversible data effect — a plain
   MVP feature ships directly. Don't gate everything; that's infra bloat a simple build
   doesn't need.
5. **Write the PRD** in `knowledge-manager`'s `TASK.md`-adjacent style — bulleted
   fields, not run-on prose: Goal, Objectives, Target Users, Feature List (each with its
   acceptance criteria), Cut for v1, Constraints.

## Relationship to other skills

- `stack-selector` consumes this PRD to pick a stack — don't make technology choices
  here.
- Every acceptance criterion written here is what the QA phase later verifies against
  and what `code-review`'s "requirements fit" dimension is checked against throughout
  Implementation — treat this document as the thing later phases are graded against,
  not a one-time formality.

## Note on project-local overrides

A repo can have its own `.claude/skills/requirements-analyst/` with different defaults
(e.g. a project that's explicitly B2B/multi-tenant from day one would want that as the
default instead of the global Scope-Cut Defaults' "single-user unless stated"). Where
both exist, the project-local one takes precedence for that repo — this global version
is the default for any repo that doesn't have its own.

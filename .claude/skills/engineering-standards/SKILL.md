---
name: engineering-standards
description: Ground backend, frontend, and fullstack code in current industry practice. Covers API design, auth, security, testing, deployment, observability for backend; components, state, performance, testing for frontend — from the repo's actual stack, never assumed. Use this whenever backend or frontend work needs grounding in real practice. Triggers include "make this backend world class", "is this scalable", "audit our API design", "review our frontend architecture", "best practice for X", "harden this service", "improve observability", "diagnose this backend/frontend issue". Do NOT use for a single fact lookup (research) or to replace task-analysis's plan or debugging's root-cause procedure.
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# Engineering standards

A portable backend/frontend/fullstack reference, not a lifecycle stage.
Grounds `architecture`, `implementation`, `debugging`, and `release-git` in
current industry practice for whatever stack the repo it's placed in
actually uses — this repository has no application code of its own, so
there is nothing to hardcode a stack against.

## SCAN — detect the stack before recommending anything

Grep the target repository's root (and one level of common subdirectories)
for the manifest a real stack always leaves behind, rather than asking or
assuming:

1. A Node manifest — read its declared dependencies for the actual
   framework (server framework means backend; UI framework means frontend;
   both present means fullstack).
2. A Python manifest — a project-metadata file or a plain dependency list.
3. A Go module file.
4. A Rust manifest.
5. A Ruby gemfile.
6. A JVM build file (Maven- or Gradle-style).

**In this repository, SCAN correctly finds nothing.** `CLAUDE.md` states
plainly there is no application code here — that is expected, not a defect.
This skill exists to be consulted while working *in* a repository that has
one (a sibling product repo, or wherever this layer is installed next), not
to describe this repository's own (nonexistent) stack.

Load only the reference file(s) matching what SCAN actually found. A
backend-only repo never needs `frontend-standards.md` open, and vice versa.

## Reference navigation

| File | Covers |
|---|---|
| `references/backend-standards.md` | Technology decision matrix, API design, auth, security (OWASP), testing pyramid, deployment, observability |
| `references/frontend-standards.md` | Component architecture, state management, data fetching, rendering performance, testing |

Visual/token/motion/accessibility-floor guidance for a frontend is **not**
here — that is `architecture/references/design-contract.md`'s design
contract. This skill's frontend file is code-level engineering only; the
two are cross-referenced, not merged, so a visual decision and a code
decision are never edited in the same place for different reasons.

## Routing

- **Consulted, not entered as a stage.** `architecture` reads the relevant
  reference once a design direction is chosen and touches backend or
  frontend code; `implementation` reads it before writing backend or
  frontend code; `debugging` reads it while diagnosing a backend or
  frontend failure, for the failure classes industry practice already
  names (connection-pool exhaustion, N+1 queries, hydration mismatches,
  memory leaks); `release-git` reads it — together with
  `release-git/references/observability-sre.md`, which already owns SLOs,
  alerts, and dashboards generically — for what to actually monitor once a
  target exists.
- **Handoff, only when this skill's own consultation implies more work
  than a read:** if the request is new work with no plan yet, hand off to
  `task-analysis`. If it names an existing failure, hand off to
  `debugging`. Otherwise, answer directly and stop — most consultations are
  a grounding read, not a new unit of work.

## Success

The repo's actual stack was detected, not assumed; the matching reference
file(s) were read before recommending anything; a backend or frontend
question was answered against a named industry practice (OWASP, a testing
pyramid, a deployment pattern) rather than a general impression of "good
code"; and no design-contract content was duplicated instead of cited.

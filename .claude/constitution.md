# Constitution

Seven articles. Every plan ticks each one or justifies the exception in writing.
This repository's constitution suite fails if an article has no gate or a gate names no
article, so the two cannot drift.

These are not aspirations. Each exists because its absence caused a specific
failure in this repository, and each is cheap to check.

## I — Evidence

No completion claim without output from a check that actually ran, quoted.
"Tests pass" is not evidence; `PASS: 25 check(s) green` is.

## II — Test first

Behaviour gets a failing test before an implementation. A test written after the
code proves the code does what it does, which is not the question.

## III — Smallest change

Change what the task requires and stop. No refactor nobody asked for, no
abstraction for a second case that does not exist yet.

## IV — Reversibility

Push, merge, publish, deploy and schema migration need explicit human approval,
every time. Prior approval of a plan is not approval of these.

## V — No silent degradation

A check that was skipped, disabled or could not run is named in the output. A
gate that quietly stops guarding still reads as coverage, which is worse than
having no gate.

## VI — Mechanism over rule

A rule the model must remember is not a mechanism. Prefer a hook, a test or a
platform setting. If a rule cannot be enforced by one of those, say so where it
is written rather than implying it is enforced.

## VII — Secrets never land

No credential enters the repository, in any file, at any time. Unrecoverable
once pushed, so the check runs before the commit, not after.

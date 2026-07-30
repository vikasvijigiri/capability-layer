# Code Review

An independent Staff Engineer pass over a pending change: requirements
fit, correctness, architecture, maintainability, security, performance,
folder organization, naming, and testing. Rejects and requests fixes
rather than approving with caveats; reviews again after a fix until it
actually passes.

Standards come from `engineering-policy` (not restated here). The
mechanical secret/debug/branch checks at actual commit/push time come from
the `git-delivery-guard` hook — this skill is the reasoning half neither
that hook nor a linter can do: judging whether the change is architecturally
sound and actually solves the stated problem.

Also owns drafting the commit message and PR/release description once a
change passes review — but never runs the delivery command itself; that's
always an explicit, separate, user-approved step.

See [`SKILL.md`](SKILL.md) for the review checklist.

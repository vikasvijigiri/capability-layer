# How does `code-review` compare to a real repo's equivalent?

**Asked because:** the same pass just run for `writing-plans` against
affaan-m/ECC's `commands/plan.md` found real gaps and real strengths on both
sides; `code-review` is the next skill due the same scrutiny before it is
trusted at delivery time.

**Comparable:** [affaan-m/ECC](https://github.com/affaan-m/ECC) (241k stars,
public, active) — `commands/code-review.md` (full, both Local and PR review
modes) and `skills/security-review/SKILL.md` (full), read against
`.claude/skills/code-review/SKILL.md` (127 lines) and its four
`references/*.md` lenses (`security-review.md` 55 lines and
`accessibility-audit.md` 59 lines read in full; `performance-engineering.md`
59 lines and `supply-chain-audit.md` 60 lines confirmed to exist by line count
only, not read in full).

**Verdict:** ours wins on mechanical enforcement (computed scope and security
gating, independent subagent dispatch), ECC wins on concreteness (worked
code examples, a fixed severity taxonomy, and a review that re-derives its
own validation state instead of trusting a prior stage's claim).

## Gaps in ours (with fixes)

**No severity taxonomy is defined anywhere in the skill or its four
references.** `SKILL.md` says "a verdict with findings at file:line" and
"every finding carries a severity" but never enumerates what severities exist
or what each one means or blocks. `security-review.md` says "rank findings by
exploitability and impact" — also no fixed scale. ECC's `commands/code-review.md`
defines CRITICAL/HIGH/MEDIUM/LOW with an explicit meaning and action for each,
applied identically across both its Local and PR modes, so two runs produce
comparable output. *Fix:* add a 4-row severity table to `code-review/SKILL.md`
(e.g. Blocker/Major/Minor/Nit, one line of meaning + action each) that all four
lens files reference instead of inventing their own vocabulary per run.

**No worked examples anywhere in the skill or its lenses — everything is
abstract procedure.** `security-review.md`'s "Procedure" is six prose steps
("Check authentication, authorization, input validation...") with zero code.
ECC's `skills/security-review/SKILL.md` pairs every one of its 10 categories
with a concrete FAIL/PASS code snippet (hardcoded secret vs env var; string-
concatenated SQL vs parameterized query; `localStorage` token vs httpOnly
cookie), making "what does this finding look like" unambiguous for whoever —
human or agent — applies the checklist. *Fix:* add 3-4 FAIL/PASS snippet pairs
to `references/security-review.md` for the highest-frequency finding classes
(secrets, injection, auth-token storage), staying within the "≈500 tokens"
terseness budget by cutting one prose step for one example pair.

**The workflow asserts "runs after verification" but never checks it.**
Line 17 of `SKILL.md` states this skill "runs after verification" as a
precondition, but nothing in the five-step workflow confirms
`tools/run_checks.py` actually ran and passed for the diff under review — the
claim is trusted, not re-derived. ECC's PR mode Phase 4 (VALIDATE) re-runs
typecheck/lint/test/build itself, per detected project type, and records
pass/fail per check in the report, regardless of what was claimed before.
*Fix:* either have `code-review` assert `tools/run_checks.py`'s last exit code
for this diff (cheap, no re-run) or explicitly document that verification
trust is intentional and out of scope, so the gap is a decision, not an
oversight.

## Where ours is ahead

**Scope and the security lens are computed, not judged.** `tools/scope.py`
classifies the diff `small`/`major`/`undetermined` and step 3 runs
`tools/security_gate.py --json`, whose exit code is not advisory — a non-zero
exit makes `references/security-review.md` mandatory and names the fired
clause. ECC's only scope guidance is prose: "Large PRs (>50 files): Warn about
review scope" — a threshold mentioned in an edge-case note, not enforced by
any script, and it always runs the same 7-category pass regardless of what
changed.

**Independent multi-angle dispatch via subagents.** For a large change,
`code-review` dispatches `diff-reviewer` (correctness/security/test-quality/
scope, independently) and `security-reviewer` (a genuinely separate security
pass), then merges duplicate findings — real parallel independent review.
ECC's PR mode is a single linear sequence of phases with no subagent
dispatch; one pass covers all seven categories serially.

**`security-review.md`'s evidence bar is stricter.** It requires marking each
control "evidenced, missing, or unverified" and writing an abuse case per
high-risk path, plus an explicit boundary: "do not call a change secure
because no issue was found; state what was and was not assessed." ECC's
checklist is a checkbox list ("[ ] CSRF tokens on state-changing operations")
that verifies presence, not that the control was exercised or its absence is
recorded as unassessed rather than passed.

## One line

Ours enforces *where to look and when to block* mechanically; ECC shows
*what a bad line of code looks like* concretely — the fix is porting a few of
ECC's worked examples and its severity table in, not rearchitecting either
side.

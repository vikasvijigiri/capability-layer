# Skill quality: `delivering` vs affaan-m/ECC

Compares `.claude/skills/delivering/SKILL.md` (200 lines) and its backing
`tools/delivery_check.py` against the closest real comparables in
[affaan-m/ECC](https://github.com/affaan-m/ECC), a large public multi-skill
Claude Code repo.

## Comparables read in full

- `commands/pr.md` (146 lines) — the functional match: discovers a PR
  template, analyzes commits/files, pushes, opens the PR via `gh pr create`.
- `skills/github-ops/SKILL.md` — broader GitHub-ops skill (issue triage, PR
  review checklist, CI debugging, releases, security alerts, ends in a prose
  "Quality Gate").
- `skills/delivery-gate/SKILL.md` — **false friend by name.** It's a Stop hook
  for session hygiene (stale learning-log mtimes, disk space, rationalization
  regex on the transcript) — unrelated to PR/push readiness. Noted, not used
  as a comparable.

## Gaps in ours (concrete, with fixes)

1. **No PR-template discovery.** `pr.md` checks four known template paths
   (`.github/PULL_REQUEST_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`,
   `.github/pull_request_template.md`, `docs/pull_request_template.md`) and
   fills them from commit/file analysis. Our step 5 says "compose the
   description yourself" but never checks for a repo-native template, so a PR
   could ship missing sections a project's own template requires. Fix: add a
   template-discovery sub-step before step 5's composition instructions.
2. **No duplicate-PR guard.** `pr.md`'s Phase 1 runs
   `gh pr list --head <branch> --json number` and stops if one already exists.
   Nothing in our Steps checks this before preparing a new PR. Fix: fold into
   step 5 or 6 as a cheap precondition.
3. **No worked example of the final report.** `pr.md`'s Phase 6 shows the
   literal rendered output (`PR #<n>: <title>` / URL / branch / change counts
   / CI summary / next steps). Our step 8 only lists the fields in prose
   ("changed paths, base, checks, conflict files, evidence") with no sample
   block — the same gap found earlier in `writing-plans` vs ECC's `plan.md`.

## Where ours is stronger (confirmed by reading the source)

1. **Push confirmation is a tool-enforced HARD-GATE; ECC has none.** `pr.md`
   Phase 3 runs `git push -u origin HEAD` unconditionally — no
   `AskUserQuestion`, no prose ask, nothing between DISCOVER and PUSH. This is
   exactly the failure our Red-Flags row "They'll probably say yes, I'll just
   push" exists to prevent.
2. **Delivery readiness is computed, not asserted.** `tools/delivery_check.py`
   (read in full) evaluates 7 facts mechanically — base-alignment, CI-for-this-SHA,
   stack depth, merge-method compatibility, divergence, worktree cleanliness,
   enforcement — with a 3-way exit code (`0` ready / `1` failed / `2`
   undetermined) that refuses to fold "unknown" into "pass." ECC's nearest
   equivalents are `pr.md` Phase 1's ad hoc bash+prose Warn/Stop table and
   `github-ops`'s closing "Quality Gate," a bare prose checklist with no
   script and no unknown/failed distinction.
3. **Stacked-PR/squash-merge interaction is handled explicitly; ECC never
   mentions it.** Ours has a dedicated table plus 3 ordered rules, backed by
   `delivery_check.py`'s `stack_depth`/`merge_methods` checks (advisory at
   depth 2, blocking at depth 4, blocking when squash is enabled at depth
   ≥2). Neither `pr.md` nor `github-ops/SKILL.md` mentions stacks, chain
   depth, or squash hazards at all — and `pr.md`'s conflict handling discovers
   conflicts by actually running the rebase, not by simulating first the way
   ours does with `git merge-tree --write-tree`.

## Verdict

ECC's `pr.md` is a tighter, more example-rich mechanical script for the happy
path (template discovery, duplicate guard, a worked report); ours is the
safer one for the actual failure modes that matter at delivery time — the
push gate, computed readiness with an honest "unknown," and stack-aware
conflict handling ECC's comparables don't address at all.

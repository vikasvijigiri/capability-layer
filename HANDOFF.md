# Handoff

<!-- Current-state snapshot. Overwrite in place each time it's updated --
this is status, not history (that's LOG.md and TASK.md's Completed section). -->

## Completed

<!-- Append-only history. Deliberately OUTSIDE the session-context markers
below -- SessionStart never re-injects this, same as TASK.md's own Completed
section. Read the file directly when full history is actually needed. -->

- 2026-08-01 — Capability layer collapsed to three skills and committed at
  `1443ba2`. Prior history reset here; `git log` from that commit back.

<!-- session-context:start -->
## Current Work

**The backlog is landing, and the gate layer is being cut from 28 hooks to 8.**
Five GitHub repos were read and they agree: every hook in all of them verifies an
*artefact* (types, lint, tests, generated files); not one enforces process. Ours
gate process compliance, which is unfalsifiable, which is why they grew to
contradict each other. `obra/superpowers` is the sharpest comparison — 14 skills,
1 hook, and its chain completes. See LOG 2026-08-02 19:26.

Decided: delete the review receipt outright; delete the dead `on-*` observability
hooks; land the backlog as several commits.

**Phase 1 is done.** The 91-file backlog landed in four commits (`92376d0`,
`4ff5ab2`, `3c383f9`, `071070b`) and the three process-compliance gates are
deleted. 28 hooks → 25. Six suites pass; `/verify` and `tools/README.md` now say
six, not seven.

Unblocked by `.claude/settings.local.json`, which the user added: the auto-mode
classifier refuses to let me edit `settings.json` or widen my own permissions,
and refuses `git rm` on repo source. Both are correct. Expect to hand the user a
command for either.

**The autonomous commit loop is live** (LOG 2026-08-02 20:50). Every turn ends in
a `wip:` checkpoint if five artefact gates pass; review moved to the push/PR.
First self-made commit: `45267c7`.

**Phase 3 is blocked on one command.** 17 `git rm`s, which the classifier refuses.
Either add `"Bash(git rm:*)"` to `.claude/settings.local.json` allow, or run the
deletion by hand — then phases 3 and 4 proceed unattended. Phase 2 (writing
`permissions`) is permanently the user's: the classifier will not let me widen my
own boundary, correctly.

**One recommendation against the approved plan:** keep
`on-artifact-create/02-hook-self-test-nudge.py`. It is on the deletion list, and
it is what forced the run that found both bugs above. Target becomes 9, not 8.

**Next: phases 2-4.** (2) move static rules into `permissions.allow`/`deny`.
(3) prune the remaining 17 to 8 — keep only what denies something irreversible
(`01-secret-scan`, `02-branch-guard`, `01-forbidden-change-guard`,
`01-spend-guard`) or acts (`03-checkpoint`, `06-artifact-autocommit`), plus
`02-bootstrap-docs` and `05-process-skill-router` which only inform. (4) one
dispatcher plus a config table, claudekit's shape. Phase 3 deletes
`04-docs-staleness`, `04-docs-sync`, `01-audit`, `02-slack`, `01-log`,
`01-context-budget`, `01-register`, `02-hook-self-test-nudge`, `02-git-tag`,
`01-rollback-notify`, `on-error/01-log`, `01-email-sim`, `01-notify`,
`06-index-scope-guard`, `03-index-baseline`, `01-env-check`.

**The git chain was run live for the first time, against a one-line file.**
`docs/2026-08-02-git-flow-walkthrough.md` records it. Subject: `dummy.py`
(`import os`), still staged and uncommitted. `Write` and `git add -- dummy.py`
passed; `git commit -m "…" -- dummy.py` was denied for real by
`pre-commit/05-docs-required.py`. That is the first end-to-end exercise of the
gates against a real change rather than a synthetic payload, and it found two
defects (both in Pending below). It is **not** the "first real end-to-end run"
Next Steps asks for — stages 1-6 were skipped, only 7's gates were exercised.

**The automation question is settled and three of its four recommendations are
done.** `docs/research/2026-08-02-automating-the-git-chain.md`: **hooks cannot
invoke skills** (official docs, fetched), so no new skill automates anything — but a
hook *can* run git, and the backlog is a missing commit boundary, not a
missing threshold.

Landed this session:

- **`post-run/05-docs-gate.py` fixed.** It had a standing trigger (the whole
  uncommitted backlog) against a per-turn satisfaction condition (doc digests vs a
  UserPromptSubmit snapshot), so above `MIN_FILES = 10` every turn demanded both docs
  be rewritten. Five blocks in one session, three talked past with its own escape
  hatch. `save_turn_marker` now records the work set too. `ISSUES.md` 2026-08-02 17:30
  carries the incident **including a wrong first diagnosis that got published** —
  read that before trusting any hook's own error text again.
- **`post-run/06-artifact-autocommit.py` written, wired and tested.** Commits prose
  artefacts (`.md` under `docs/specs|research|plans/`, `decisions/`, and the root
  knowledge docs) at the `knowledge-manager` boundary, by explicit pathspec.
  Never `git add .`, never `.claude/`, never code, never pushes.
- **`decisions/2026-08-02-gate-on-blast-radius.md`** — the three-band rule, with the
  file-count threshold explicitly rejected on evidence.
- **The staging hole is closed.** `session-start/03-index-baseline.py` records what
  an earlier session left staged (git cannot tell "staged now" from "staged
  Tuesday"), and `pre-commit/06-index-scope-guard.py` asks before a blanket
  `git add` or before a commit spends inherited files. A pathspec commit is exempt
  by design and by test — without that, the auto-commit hook would deadlock against
  it. `ALLOW_WIDE_STAGE=1` overrides.
- **`/git-state`** — granular git accounting, eight sections, every command verified
  against this repo before shipping. Counts only; judging is `/wip`'s job.
- **Two new suites**: `test_artifact_autocommit.py`, `test_index_scope_guard.py`.
  `CLAUDE.md`, `/verify` and `hooks_registry.json` updated to say seven.

Seven suites pass: `All hook tests passed`, `All process-router tests passed (11
entries routed)`, `All hook-registration tests passed (28 hooks, 13 events)`,
`All docs-gate tests passed`, `All docs-staleness tests passed`,
`All artifact-autocommit tests passed`, `All index-scope-guard tests passed`. Not
re-run this session: env-check, the broken-path-reference sweep. `compileall` was
clean at 17:30, before the last six file edits.

**In flight**: `docs/specs/2026-08-02-brainstormer-grounding-design.md` is
written and approved section-by-section, **not implemented and not committed**.
Adds two bounded evidence phases to `brainstormer` (seed before the clarifying
questions, kill after approaches), a mandatory `## Prior art` spec section, and
five mechanical rules in `tools/test_docs_gates.py`. Next step for it is
`writing-plans`; nothing has been handed off yet.

**Uncommitted and unreviewed**: 89 paths — 50 staged (49 `docs/archive/` renames
plus `.claude/workflow.md`, all rename-only: `0 insertions(+), 0 deletions(-)`),
22 modified, 17 untracked. The three buckets overlap; `/git-state` breaks it down.

Eleven skills, `11 entries routed`, every workflow stage owned. The chain is
1 `task-brief` → 2 `brainstormer` → 3 `writing-plans` → 4 `executing-plans` →
5 `verifying-work` → 6 `code-review` → 7 `delivering` → 8 `releasing` →
9 `knowledge-manager`, with `research` and `systematic-debugging` entered from
any stage and returning to it. `.claude/workflow.md` owns that ordering and
`tools/test_process_router.py` asserts the skills agree with it.

Stage 8 is new this session and is the only stage **skipped by absence rather
than judgement**: `delivering` branches to it when the repo has a deploy target
and straight to 9 when it does not. Stages 7 and 8 take separate approvals, and
8's is per target.

## Pending

- **No skill has ever been run end to end** except `code-review`,
  `task-brief` and `knowledge-manager`. Eleven skills now assert their own gates,
  handoffs and file paths in their own text. The superpowers Iron Law — a
  baseline pressure run *without* the skill — is unmet on all eleven. This is
  the largest standing risk and it has not moved in four sessions.
- **`releasing` cannot be dogfooded in this repo — there is no deploy target.**
  Unique among the stages. Either accept it as permanently unexercised here, or
  exercise it against a throwaway target (a static page on a free tier) once, to
  prove the detect → state → deploy → smoke → roll-back sequence survives contact.
  Its `references/` directory is deliberately empty; the first real target earns
  the first pack file, and `SKILL.md` must not grow a platform branch.
- **`.claude/` structure audit, 2026-08-02 — three findings, none actioned.**
  (1) Hook directory names describe a lifecycle that does not exist: 13
  directories map to 7 real events, and 6 names are fiction against
  `settings.json` — `pre-commit/` and `pre-deploy/` are both `PreToolUse` on
  `Bash|PowerShell`; `on-error/`, `on-validate-fail/` and `on-deploy-failure/`
  are all `PostToolUseFailure`. Nothing is broken; "which hooks fire when I
  commit?" is just unanswerable from the tree. Renaming to event names would
  touch `test_hooks.py` and `session-start/01-env-check.py`, which hardcode the
  current names. (2) `.claude/agents/` (all four) and five skill directories are
  **untracked** — in a repo whose product is `.claude/`, git holds six of eleven
  skills and zero agents. (3) Verified correct against the official docs and
  needing no change: `.claude/agents/<name>.md`, `skills/<name>/SKILL.md`,
  `commands/*.md`, and every event name in `settings.json` including
  `PermissionRequest` and `PostToolUseFailure`.
- **`docs/plans/` is still empty**, so `executing-plans` has never had input.
  `writing-plans` has never produced a plan. Stages 3→4 are untested as a pair.
- **The chaining is prompted, not enforced.** Each skill carries an imperative
  `## Next step`, but no hook can fire when a skill finishes, so nothing detects
  a chain that stops early. If chaining needs to be real, that is a runner
  (`workflow.yml` + `tools/`), which is a project, not an edit.
- **Descriptions cost ~1,215 tokens every session** (4,861 chars over ten
  skills, ~7× superpowers per skill) and duplicate the routing file's job. The
  trade is deliberate — see LOG 2026-08-02 — but the test that would let them
  be cut safely does not exist: replay the real phrasings and confirm the router
  still lands them.
- **RESOLVED — blast-radius banding adopted**, see
  `decisions/2026-08-02-gate-on-blast-radius.md`. Three bands, and the file-count
  threshold rejected on evidence. Kept here only as a pointer.
- **A pre-execution consistency gate is missing.** spec-kit runs `analyze`
  (spec vs plan vs tasks, coverage gaps) *before* implementing. Here that check
  lives inside `executing-plans`' opening scan rather than as its own stage.
  Deliberate, and worth revisiting once a plan has actually been executed.
- **`04-delivery-guard.py` false-positives on Windows paths.**
  `find_ai_attribution` scans the whole command string and `_STANDALONE`
  excludes `/` but not `\`, so any path containing `\claude\` reads as AI
  attribution. Fix: add `\\` to both lookaround character classes. Untouched.
- **`changed_files()` is duplicated** across `pre-run/04-docs-staleness.py` and
  `post-run/05-docs-gate.py`, with a third near-copy in
  `pre-commit/05-docs-required.py`. `_hooklib.py` is where it belongs.
- **Nothing asserts that a skill's shell commands resolve.** Deleting
  `03-review-gate.py` broke `code-review` and `delivering`, both of which
  instructed running it by path, and `test_process_router.py` stayed green —
  it checks routing entries and frontmatter, not claims. Found by `grep`, fixed
  by hand. A suite that extracts every ``` block from `.claude/skills/**` and
  asserts each named path exists would have caught it, and is the highest-value
  test this repo does not have.

- **`04-delivery-guard.py` false-positives on `git merge-base`** — a read-only
  query — because it matches the verb anywhere in the command. It can `deny`, and
  `decisions/2026-08-01-review-gate-matches-verbs-anywhere.md` says that reasoning
  is correct for `ask` and wrong for `deny`. Second known false positive in this
  hook; the `\claude\` Windows-path bug below is the first. Both unfixed.
- **The review of this session's 39 files found five defects and none is recorded
  as reviewed.** All five are fixed, but the diff moved afterwards, so there is
  **no receipt** and `pre-commit/03-review-gate.py` will keep asking — correctly.
  A re-review of the updated diff is the next step for delivery.
- **`post-run/06-artifact-autocommit.py` has never fired in this repo.** Wired,
  documented, and covered by 24 cases in `tools/test_artifact_autocommit.py` against
  a throwaway git repo — but every one of those runs is synthetic. It commits, so the
  first real firing deserves watching: confirm it takes only the prose artefacts,
  leaves the index alone, and that `git log -1` looks right. Two bugs were caught by
  the tests and would both have been invisible in review (see `ISSUES.md`
  2026-08-02 18:10).
- **`ALLOW_UNLOGGED_COMMIT=1` is unreachable from a tool call.** Set inline in a
  Bash command it does not reach `pre-commit/05-docs-required.py`, which reads
  Claude Code's own environment. Every hook message that advertises the override
  is therefore advertising something an agent cannot do — only the user can, via
  `settings.json` `env` or the shell that launched Claude Code. Either the
  message says so or the hook learns to parse a leading assignment.
- **`pre-commit/05-docs-required.py` judges the index, not the commit.** It counts
  `git diff --cached --name-only`, so a pathspec commit of one file is blocked by
  the 50 staged files it would not have committed — observed live 2026-08-02 18:08.
  `06-index-scope-guard` has `PATHSPEC_COMMIT_RE` for exactly this; `05` has no
  equivalent. Arguably correct as-is (those 50 really are unrecorded), so this is a
  decision to make, not a bug to fix silently. Whichever way it goes, the two hooks
  should agree on whether a pathspec commit is scoped.
- **`04-delivery-guard.py` reads git output as cp1252.** `UnicodeDecodeError:
  'charmap' codec can't decode byte 0x90` from a subprocess reader thread on a push
  payload, 2026-08-02. Fails open and still emitted its `ask`, so nothing was lost.
  Third known defect in this hook (Windows `\claude\` paths and `git merge-base`
  above are the other two); all three unfixed. Fix is `encoding="utf-8",
  errors="replace"` on the `subprocess.run`, as `03-review-gate.py` already does.
- **The index is dirty across sessions.** 49 files staged since an earlier
  session means any commit sweeps them in. Decide per commit: `git commit -- <path>`
  (index untouched), reset to stage one file, or log and land everything at once.

## Next Steps

From `docs/research/2026-08-02-automating-the-git-chain.md`, in order:

1. **Fix `post-run/05-docs-gate.py`** before adding any mechanism. A gate that
   cannot be satisfied by obeying it trains its own bypass, and did.
2. **Let one hook commit rather than ask.** Narrowest version: on `Stop`, when the
   *only* changed files are the knowledge docs, commit them with a generated
   message. Zero blast radius, not code, no review receipt needed, and it removes
   the most frequent block. `git commit -F` with an explicit pathspec — **never
   `git add .`**.
3. **Record the blast-radius decision** in `decisions/` — gate on blast radius,
   not on phase. Three independent supports, still only a bullet here.
4. **Do not add a twelfth skill**, and defer the external runner until one plan
   has run end to end.

Then **decide the index question above** and `writing-plans` on the brainstormer
grounding spec — approved and waiting, and the first spec here that would
exercise stages 2→3 as a pair.

Then `code-review` over the non-archive entries, then commit — **and get
`.claude/agents/` and the five untracked skill directories into git in that
commit**, since they are the ones a teammate currently cannot see at all. The
archive move is 50 more entries and reviews as one decision, not fifty.

After that, the highest-value work is a **first real end-to-end run**: take one
small real change from `task-brief` through to `delivering` and record where the
chain actually breaks. Everything else here is speculation until that happens.

## Open Questions

- Does the `agent:` frontmatter field actually dispatch a subagent? Supported and
  parses, but no skill uses it.
- `post-run/05-docs-gate.py` blocked a turn on 2026-08-02 — the first observed
  `Stop` block in this build. CLAUDE.md still documents `Stop` blocking as
  "unproven"; that line needs correcting, and it is worth knowing whether the
  block is reliable or was a one-off.
- Several claude.ai connectors (Asana, Atlassian, Box, Canva, HubSpot, Intercom,
  monday.com) need OAuth and cannot be authorised from a non-interactive session.
<!-- session-context:end -->

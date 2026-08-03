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

**Two repos now.** This one is the capability layer; `../physrun/` is the first
product built with it.

| Repo | Branch | Commits | State |
|---|---|---|---|
| `Notes` (UAIOS) | `collapse-capabilities-into-routing` | 26 | clean; 6 suites, ruff, mypy green |
| `../physrun/` | `capability-layer` | 10 | clean; 50 tests, lint/typecheck green |

Neither has been pushed. physrun has no remote at all.

**physrun** is a content-addressed run store for computational theoretical
physics: an identical calculation is a cache hit, every result is re-executable
from its id. Spec and plan are in `docs/specs/` and `docs/plans/` here, both
dated 2026-08-03, all 40 plan steps ticked. It has its own `CLAUDE.md`, six
hooks and knowledge docs — a *deliberate subset*, because UAIOS's `CLAUDE.md`
asserts things ("no application code here", a hook count) that are false there.

**The chain ran end to end for the first time.** `brainstormer` →
`writing-plans` → `executing-plans` → `verifying-work`, producing a real
product. That was the top item in Next Steps for two sessions and it is done.

**The gate layer is 9 hooks and stable.** Phases 1 and 3 of the prune landed
2026-08-02; phase 2 is permanently the user's (the classifier will not let me
widen my own permissions); phase 4 was dropped on the argument that a dispatcher
earns nothing at 9 hooks in 7 directories.

**The diagnose loop is live in both repos.** Red writes a report and names
`systematic-debugging`, three strikes on one failure escalates, green closes
forward into `verifying-work` → `code-review` → `delivering`. It suggests and
never blocks, because the hook that blocked deadlocked and was deleted.

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

The chain has now run end to end once — `task-brief` was skipped by design,
`brainstormer` → `writing-plans` → `executing-plans` → `verifying-work` all ran,
and a real product came out. That was the highest-value open item and it is done.

1. **Fix the branch guard** (`ISSUES.md` 2026-08-03 14:20). It reads the
   session's repo, not the command's target, and let eight commits onto a
   protected branch. Highest-value fix here because it is a guard that reports
   nothing while failing.
2. **Task 9 — physrun has no skills or agents.** Its hooks fire; a session opened
   there has no `code-review`, no `writing-plans`. Decide whether the eleven
   skills are portable as-is or need a physrun-specific cut; UAIOS's `CLAUDE.md`
   proved not portable, and the skills may not be either.
3. **The slow tier has never run against anything.** `--tier slow` returns
   `no checks detected` in both repos. physrun will exercise `build` and `audit`
   as soon as it has a package to build; `e2e` and `smoke` need a UI or server,
   which the run substrate does not have.
4. **Decide physrun's `main`.** Eight commits sit on it that the guard should
   have refused. Local and unpushed, so rewriting is still cheap if wanted.
5. **Nothing has been pushed from either repo.** No remote exists for physrun.

## Open Questions

- **Are the eleven skills portable?** `CLAUDE.md` was not — it asserts "there is
  no application code here" and a hook count, both false elsewhere. Skills may
  carry fewer repo-specific claims, but `test_referenced_paths.py` would be the
  way to find out rather than assumption.
- **Should the diagnose loop's three-strike budget be per-signature or per-day?**
  Currently per-signature and reset by any different failure, which is right for
  a converging fix and wrong for a flaky test that alternates.
- Does the `agent:` frontmatter field actually dispatch a subagent? Supported and
  parses, no skill uses it, and **zero subagents have been dispatched** in this
  repo's history.
- Several claude.ai connectors (Asana, Atlassian, Box, Canva, HubSpot, Intercom,
  monday.com) need OAuth and cannot be authorised from a non-interactive session.
<!-- session-context:end -->

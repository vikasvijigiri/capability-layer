# Issues

<!-- Append-only, newest entry at the TOP, never rewrite old ones -- same discipline
as LOG.md. One entry per incident (the whole diagnose/fix sequence), written by the
systematic-debugging skill once its four-phase loop reaches a terminal state.
Format: ## YYYY-MM-DD HH:MM -- <short symptom title>, fields per the ISSUES.md section
of knowledge-manager's formats.md. Not preloaded at SessionStart -- consulted on demand. -->

## 2026-08-07 — the trigger eval measured its own instrument, and it cost $29

- **Symptom**: `tools/eval_triggers.py` reported `trigger_rate 0.1` for both
  `code-review` and `systematic-debugging`, with `false_fire_rate 0.0`. Read
  naively that says the descriptions almost never fire.
- **Why it was not believed**: two unrelated skills scoring *identically* at 0.1,
  with a flawless 0.0 on negatives, is the shape of a broken detector rather than
  two independent prose failures. `systematic-debugging`'s own rule applies —
  make the harness deterministic before trusting its verdict.
- **Root cause**: `run_query` invoked `claude -p --output-format json`. That
  format returns a **result summary only** — `result`, `usage`, `total_cost_usd`,
  `session_id` — and carries no tool-call record at all. Grepping it for a skill
  name could only match if the closing prose happened to name the skill. Every
  real trigger was unobservable, so 0.1 was noise, not signal. Confirmed by
  dumping one response's keys.
- **Fix**: `--output-format stream-json --verbose`, parsed per line, reading
  `tool_use` blocks. Verified on a trivial prompt: `tool_use names: ['Read']`.
- **Two things added because their absence caused this**: the harness now returns
  and prints **cost** (one query measured $0.72, so the blind 40-query run was
  ~$29), and takes `--limit N` so a harness change can be validated for a few
  dollars instead of thirty. The spend guard now quotes a price:
  `~$6 at the measured per-query rate`.
- **Status**: **Resolved for the instrument; the measurement itself is still
  unknown.** No claim about description quality survives this — the earlier 0.1
  is withdrawn, not restated with a caveat.

## 2026-08-07 — the branch guard's cross-repo bypass came back, one flag wider
- **Phase/Context**: `code-review` at stage 7 on the 452-file rebuild branch,
  routed here on a P1. Full tier was green throughout — this bug is invisible to
  every check the repo has, which is the point.
- **Symptom**: none. No error, no output. `02-branch-guard.py` resolved the
  **session's** branch instead of the command's target for
  `git --no-pager -C ../other commit`, so a commit onto a sibling repo's
  protected `main` would have been allowed silently. Identical class to
  2026-08-03 14:20, which cost eight such commits.
- **Root cause**: `GIT_C_RE = r"\bgit\s+(?:-\w+\s+\S+\s+)*-C\s+..."` assumes every
  git global flag is `-x value`. Boolean globals consume no value, so the
  repetition cannot pass them, and `-\w+` cannot match a `--long` flag at all
  (`-` is not `\w`). Four of git's documented globals defeat it: `--no-pager`,
  `-P`, `--paginate`, `--literal-pathspecs`. Reproduced before any fix:

      git -C /t commit                     -> /t
      git --no-pager -C /t commit          -> None   <-- guard reads session repo
      git -P -C /t commit                  -> None
      git --paginate -C /t commit          -> None
      git --literal-pathspecs -C /t commit -> None

- **The deeper cause, and the actual fix**: *three* implementations of "which repo
  does this command touch" existed — `02-branch-guard.py` (regex),
  `03-attribution-guard.py` (a different, looser regex that got all seven cases
  right), and `_hooklib.is_git_commit` (a tokeniser, for the adjacent question).
  They disagreed, and the weakest one was guarding the protected branch. Fixing
  only branch-guard's regex would have left two copies free to diverge again —
  which is exactly what happened between 2026-08-03 and now. So the fix is
  `_hooklib.git_dash_c` + `git_target_dir`, tokenisers that walk git's flag region
  against `VALUE_FLAGS` the way `is_git_commit` already did, with both hooks
  delegating and **no second copy left**.
- **Attempt that was rejected before being made**: patching `GIT_C_RE` to also
  match boolean flags. Rejected because `_hooklib` line 164 already records the
  outcome of that approach — *"a regex was tried first and got this wrong in both
  directions"* — and because it leaves the three-implementation divergence intact.
  The bug recurring in a file whose comment explains why regexes fail here is the
  evidence that the copy, not the pattern, is the defect.
- **Verification**: four failing cases written into `tools/test_hooks.py`
  `TARGET_CASES` first and watched fail (`-> ...\notes, want ...\FDE_Vikas`), then
  all ten pass. End-to-end against a real temp repo on `main`: all four forms
  `DENIED`. Whole `pre-commit` event fired via `run_hook.py`. Tier:
  `PASS: 26 check(s) green (lint, test, typecheck); audit disabled`.
- **Status**: **Resolved.**

## 2026-08-07 — package-lock.json contradicted its own manifest
- **Symptom**: `package.json` declared zero dependencies while the lockfile still
  pinned `@anthropic-ai/claude-agent-sdk` plus its transitive tree (per-platform
  sharp binaries, zod) — stale evidence sitting against
  `decisions/2026-08-07-one-workflow-engine.md`, which states the dependency was
  removed. `npm ci --dry-run` reported `remove zod / @img/sharp-win32-x64 /
  @anthropic-ai/claude-agent-sdk`.
- **Root cause**: the SDK and `tools/run_workflow.mjs` were deleted and
  `package.json` rewritten by hand; the lockfile was never regenerated, because
  nothing in the repo runs `npm` any more — `audit` is `false` by decision.
- **Fix**: `npm install --package-lock-only`, then `npm ci` to reconcile
  `node_modules`. Lockfile now has one package entry and no dependencies;
  `npm ci --dry-run` reports `up to date`.
- **Status**: **Resolved.** Not a build break at any point — `npm ci` reconciles
  rather than erroring — but a decision record and the tree disagreed, and the
  tree is what a reader checks.

## 2026-08-03 17:05 — the layer installer is written twice, and it has already drifted once
- **Phase/Context**: no-slop sweep at `--scope layer`, fired by
  `07-layer-drift.py` after `global-session-start/` was added. Script green
  (`All no-slop tests passed`, 45 tracked files); both findings are judgement.
- **Symptom**: two hooks now shell out to `.claude/install.py` with near-identical
  supporting code — `git()` at
  `on-repo-create/01-layer-import.py:63` and `global-session-start/01-layer-bootstrap.py:73`,
  `install()` at `:150` and `:123`, and the same `GUARD` constant at `:60`/`:62`.
  The refusal sets are the same rules stated in different words.
- **Evidence it is not theoretical**: the UTF-8 encoding bug found while testing
  the new hook (installer stdout decoded as cp1252, reaching the session as
  `stage 5 â€" 4 uncommitted`) had to be fixed **in both files**, and
  `01-layer-import.py:154` now carries a "see the other file" comment. That
  pointer is the paraphrase-drift smell starting, one session in.
- **Blast radius of a change**: a refusal-rule edit needs six files — both hooks,
  both `hooks_registry.json` descriptions, and both `CLAUDE.md`s.
- **Checked and rejected as separate findings**: the two hooks never fire for the
  same target (different events; the second sees `.claude/skills/` and goes
  silent — verified against a throwaway git repo). `~50 files` in the docstrings
  is accurate; `56` measured.
- **Status**: **Open, deliberately not fixed.** Reported at stage 6 and the user
  chose report-only. The shape of the fix is a shared `_layerinstall.py` with the
  two hooks as thin event adapters; the cost is that both must then be re-fired
  against realistic payloads, because a hook's failure symptom is silence.

## 2026-08-03 17:05 — every install target receives a hook that can never fire there
- **Phase/Context**: same sweep. `install.py:57` — `LAYER` copies `hooks/`
  wholesale, so `global-session-start/01-layer-bootstrap.py` lands in every
  target repo.
- **Symptom**: it is wired only in `~/.claude/settings.json`, by absolute path
  into this repo. In a target it is on disk, declared in the copied registry, and
  fires nowhere. Inert today.
- **Why it is worth an entry anyway**: if anyone later wires it in a target, that
  target silently becomes a second global install source competing with this one,
  and both would act on the same session.
- **The argument for leaving it**: `install.py` already copies *itself* into
  targets, deliberately — `install.py:52` states that a layer which cannot
  propagate itself is copied once rather than portable. Excluding the deployer
  while including the installer would contradict that.
- **Status**: **Open, unresolved by design.** Needs a policy call about what a
  target should receive, not an edit inside a sweep.

## 2026-08-03 14:20 — the branch guard reads the wrong repository
- **Phase/Context**: building `../physrun/` from a Claude Code session rooted in
  this repo. Eight commits were made with `cd ../physrun && git commit …`.
- **Symptom**: all eight landed on physrun's `main`, which is in
  `PROTECTED_BRANCHES`. `pre-commit/02-branch-guard.py` was registered and firing
  the whole time and denied none of them. Discovered only when physrun's own copy
  of the auto-commit refused with "`main` is a protected branch" — the guard
  working correctly, from inside the right repo, on the ninth attempt.
- **Diagnosis**: the guard resolves the branch from `payload["cwd"]`, which is the
  **session's** working directory, not the directory the command actually runs in.
  A `cd` inside the command string is invisible to it. So it read *this* repo's
  branch (`collapse-capabilities-into-routing`, unprotected) and allowed a commit
  onto a different repo's `main`.
- **Why it was invisible**: the guard did exactly what it was written to do and
  said nothing, which is indistinguishable from having checked and approved. Every
  hook here fails this way; it is why the repo's own rule is that a hook's failure
  symptom is silence.
- **Status**: **Resolved 2026-08-03 15:40.** Two independent bugs had to stack for
  those eight commits to land, and either alone was sufficient:
  - `target_dir()` now resolves the branch from the command's actual target —
    the last `cd`, then any `git -C`, falling back to the session cwd when the
    path does not exist.
  - The `COMMIT_RE` regex **never matched `git -C <dir> commit` at all**, because
    `-C` takes a value and `(?:-[^\s]+\s+)*` cannot consume it. So the guard was
    skipping the check entirely, not merely checking the wrong repo.
- **The second bug was a regression of a solved problem.** `05-docs-required.py`
  had a tokenising `is_git_commit()` with a docstring explaining this exact
  failure — and deleting that hook on 2026-08-02 deleted the only correct
  implementation. Recovered from `350dec2^` and promoted to
  `_hooklib.is_git_commit`, now shared by both surviving pre-commit hooks rather
  than copied into each.
- **Verified**: with the session on an unprotected branch and the target repo on
  `main`, `cd <dir> && git commit` and `git -C <dir> commit` both deny; a
  same-repo commit and `--dry-run` both pass. Regression tests in
  `tools/test_hooks.py` cover seven `is_git_commit` shapes and four
  `target_dir` cases.
- **Not fixed**: the eight commits already on physrun's `main`. Local and
  unpushed, so still cheap to rewrite.
- **Blast radius**: any repo edited from a session rooted elsewhere. In this case:
  eight commits on a protected branch that should have been refused. Recoverable —
  physrun is local, unpushed, and now on `capability-layer`.

## 2026-08-02 18:10 — the new auto-commit hook committed nothing, and said it succeeded
- **Phase/Context**: first test run of `post-run/06-artifact-autocommit.py`, before it
  had ever fired for real.
- **Symptom**: the hook reported a successful commit; `git show --name-only HEAD`
  returned an empty list. Two separate causes, both invisible in review, both fatal to
  the hook's entire purpose.
- **Diagnosis**:
  - **(a) A pathspec commit cannot commit an untracked file.** `git commit -F msg --
    <paths>` fails with "did not match any file(s) known to git" when a path is
    untracked — and a *brand-new* spec, research doc or decision record is always
    untracked. The hook's only real use case was the one case it could not handle.
  - **(b) `git status --porcelain` collapses untracked directories.** A new
    `docs/specs/` reports as one entry `?? docs/specs/`, not `?? docs/specs/s.md`. The
    trailing slash never matches `.endswith(".md")`, so every file in a new directory
    was invisible to the artefact filter.
- **Attempts**:
  - 1. Wrote 24 test cases against a throwaway git repo before the first real firing →
    caught both bugs immediately. Had it been wired and left untested, it would have
    reported success while committing nothing, indefinitely.
  - 2. Fixed (a) by staging the computed paths first with `git add -- <paths>` →
    revealed (b), because the spec still did not appear in the commit.
  - 3. Fixed (b) with `git status --porcelain -uall` in `_hooklib.changed_paths` →
    both resolved.
  - 4. Two test assertions were themselves wrong and had to be corrected, not the code:
    one expected `["LOG.md", "docs/specs/s.md"]` when `HANDOFF.md` legitimately belonged
    in the commit; one stubbed *every* git call, so it only ever exercised the `add`
    failure path and never the `commit` one. **The "does not sweep" case initially
    passed for the wrong reason — nothing was being committed at all.** A green test
    over a dead code path is worse than a red one.
- **Fix**: `git add -- <explicit paths>` before the pathspec commit (still impossible to
  sweep, since the paths are the computed artefact list); `-uall` on the shared
  `changed_paths`, which also makes the docs gate's work-set comparison see new files.
  Failure messages now distinguish the stage failure (index unchanged) from the commit
  failure (files left staged), so the recovery differs correctly.
- **Status**: `Resolved` — `All artifact-autocommit tests passed` (24 cases), and all
  six suites green including `All hook-registration tests passed (26 hooks, 13 events)`.
  **Still unproven in this repo**: the hook has never fired outside the temp-repo tests.

## 2026-08-02 17:30 — the docs gate blocked five turns in a row and could not be satisfied
- **Phase/Context**: `post-run/05-docs-gate.py`, the `Stop` gate that refuses to end
  a turn leaving substantial work unrecorded. Backlog stood at 83-84 uncommitted files.
- **Symptom**: blocked five consecutive turns in one session, including turns that
  produced nothing but an explanation. Its escape hatch ("say it is mid-flight") was
  used three times rather than the gate being fixed, which is precisely how a gate
  stops being read. Writing both docs satisfied it for exactly one turn.
- **Diagnosis**: a **scope mismatch between trigger and satisfaction**. The trigger is
  standing — `work` is the entire uncommitted backlog from `git status --porcelain`.
  The satisfaction condition is per-turn — doc digests compared against the snapshot
  `save_turn_marker` takes at UserPromptSubmit. So once the backlog passed
  `MIN_FILES = 10`, *every* later turn tripped it, because the backlog is always there
  and the docs are only written on the turns that finish a unit of work. Proof:
  marker and live digests byte-identical (`d732eb51…` / `2278db69…`) on a turn where
  the docs had been correctly written the *previous* turn.
- **Attempts**:
  - 1. Diagnosed from the block message alone as an mtime comparison against
    `docs/archive/ARCHIVE.md`, and recorded that in `LOG.md` and `HANDOFF.md` →
    **wrong, and the wrong diagnosis was published**. The hook performs no mtime
    comparison at all; lines 90-98 document that mtimes were removed on 2026-08-01
    after three false blocks. The `reason` text still said "older than the newest of
    them" — leftover prose from the removed implementation, which is what misled the
    diagnosis. **Instance eight of this repo's recurring failure: prose declaring a
    mechanism the wiring does not implement.** Corrected in the 2026-08-02 17:30
    `LOG.md` entry.
  - 2. Read the hook and `_hooklib` in full, then reproduced by comparing marker to
    live digests → root cause named: standing trigger, per-turn satisfaction.
  - 3. Added two failing tests before touching the hook → both failed for the right
    reason (`stop gate silent when this turn added no work`; `block reason does not
    claim an mtime comparison it no longer performs`).
- **Fix**: `save_turn_marker` now snapshots the **work set** alongside the doc digests,
  so the trigger is per-turn too; the gate returns silently when `sorted(work)` equals
  the turn-start set. `changed_paths`/`work_paths` moved into `_hooklib` so the writer
  and the reader cannot diverge — two near-copies would have made the comparison
  meaningless. Marker stores `None`, not `[]`, when git cannot answer, so "no work at
  turn start" stays distinguishable from "unknowable"; only the first excuses a turn.
  A legacy marker with no `work` key keeps the old blocking behaviour rather than
  silently going quiet. Reason text rewritten to describe what the code does.
- **Status**: `Resolved` — `All docs-gate tests passed` (19 cases), and firing the hook
  directly on the real repo returns `decision: block` with
  `This turn changed files and LOG.md and HANDOFF.md were not written during it
  (83 files uncommitted in total)`.

## 2026-08-02 02:10 — a hook read its own command output as user approval
- **Phase/Context**: Adding transcript-based sign-off detection to
  `03-review-gate.py`, so `--record` could not forge a receipt.
- **Symptom**: `--record` reported `Sign-off found: 'Approve'` and wrote a receipt on
  a turn where the user had approved nothing. Four distinct causes, each found only
  by running it against the live transcript rather than a fixture.
- **Diagnosis**: the sign-off scan admitted text it should never have treated as the
  user speaking.
  1. It scanned the whole AskUserQuestion envelope, so the wording of a *question*
     I wrote could match.
  2. It matched anywhere in an answer, so the option label "I review, you approve"
     — chosen turns earlier for a question about who reviews — counted as approval.
  3. The window was four user turns, so a genuine "Approve" click about a *task
     brief* six turns back satisfied a review sign-off.
  4. Worst: the envelope test was `ANSWER_ENVELOPE in body`, and a `tool_result`
     from Bash is also role `user`. A diagnostic command of mine printed the phrase
     "Your questions have been answered", so **its own stdout authorised the commit**.
     Command output is attacker-adjacent input — a grep hit or log line can contain
     any text at all.
- **Attempts**:
  - 1. Strip the question, keep only answer values → fixed (1), not (2).
  - 2. Require the approval word within the first 3 words of a line → fixed (2);
     position discriminates where wording could not.
  - 3. Narrow the window to the single most recent user turn → fixed (3).
  - 4. Require the envelope to *start* the message, not appear in it → fixed (4).
- **Fix**: all four, plus nine regression assertions in `tools/test_hooks.py` naming
  each failure. `--record` now refuses with exit 2 and needs `--force` for mechanism
  tests. Verified in both directions: refuses with no sign-off, records with one, and
  `04-delivery-guard.py` notes only when no sign-off is findable.
- **Status**: `Resolved` — with a stated limit: this proves approval was the user's
  most recent act, never *what* they approved. It is a speed bump, not a proof; the
  skill's HARD-GATE remains the real control.

## 2026-08-01 21:15 — every review receipt erased itself the instant it was written
- **Phase/Context**: Building the `code-review` skill, running the brief's Done-check
  that a recorded review should make `03-review-gate.py` fall silent.
- **Symptom**: `--record` reported success, and the very next identical payload still
  returned `ask`. The 2026-08-01 receipt had been reporting "the change has been
  modified since it was reviewed" for the same reason, read at the time as a stale
  review rather than a broken one.
- **Diagnosis**: `.claude/hooks/state/review-receipts.json` is tracked and not
  gitignored. The fingerprint is built from `git status --porcelain` plus the two
  diffs. Writing the receipt modifies a tracked file, so all three inputs change, so
  the digest computed after recording never matches the digest recorded. Self-erasing
  by construction. The gate had never been able to pass in any repo state.
- **Attempts**:
  - 1. Checked receipt-key casing (`root.lower()` on both sides) → matched, not the cause.
  - 2. Checked whether `record()` and the hook path resolve the same root → identical.
  - 3. Checked whether the receipts file appears in `git status` → it does. That is it.
- **Fix**: Added `RECEIPTS_PATHSPEC = ":(exclude).claude/hooks/state/review-receipts.json"`
  and applied it to all four fingerprint inputs, including the PR branch diff. Verified
  the full cycle: ask → record → silent → one byte changed → ask → reverted → silent.
  Gitignoring the file would also work; excluding the path holds either way and does
  not change what is committed.
- **Status**: `Resolved`

## 2026-08-01 19:55 — a skill's description silently vanished and it stayed listed
- **Phase/Context**: Rewriting the three skills' descriptions against the superpowers
  standard, expanding them with quoted trigger phrases.
- **Symptom**: The skill listing rendered `brainstormer: Brainstormer` — the bare H1
  title in place of the description. The skill was still listed, still routed, and
  untriggerable by description. No test failed. No hook complained.
- **Diagnosis**: The new text contained `...not yet settled: "any ideas"`. A
  colon-space-quote inside an unquoted YAML scalar makes the parser read the value as a
  mapping, and the `description` key silently resolves to something that is not a
  string. `/skills-doctor` documents this exact failure; nothing executed that check.
- **Attempts**:
  - 1. Noticed only because the listing re-rendered in view mid-turn. Nothing in the
    four suites was watching → the detection was luck, which is the real finding.
  - 2. Rewrote the description to avoid `: "` → description returned.
- **Fix**: Rewrote the text, then closed the detection gap: `tools/test_process_router.py`
  now asserts per skill that the frontmatter parses to a mapping, the description is
  non-empty, `name` matches the directory, and the frontmatter is within the 1024-char
  spec limit. Proved by planting `: "` back into `task-brief` and confirming
  `FAIL: task-brief frontmatter parses -- mapping values are not allowed here`.
- **Status**: `Resolved`

## 2026-07-30 21:10 — `tools/run_hook.py` hangs indefinitely
- **Phase/Context**: After rewriting the hook scripts to read their payload from stdin so
  Claude Code could invoke them directly.
- **Symptom**: `python tools/test_hooks.py` never returned. No error, no output past the
  first event — the process simply sat there until killed.
- **Diagnosis**: `run_hook.py` spawns each hook with `subprocess.run([...], env=env)` and
  no `stdin` argument, so the child inherits the parent's stdin. When the parent was
  itself launched from a pipe, that handle never reaches EOF, and `sys.stdin.read()`
  blocks forever. The `isatty()` guard does not help: an inherited pipe is not a TTY, so
  the check passes and the read still blocks.
- **Attempts**:
  - 1. Ran the same suite earlier and it passed → misleading; stdin happened to be at EOF
    in that context, so the bug was invisible rather than absent.
  - 2. Reordered `_hooklib.load_payload()` to read `HOOK_PAYLOAD` before stdin → fixed.
- **Fix**: `load_payload()` checks the env var first. `run_hook.py` always sets it, so the
  only caller that leaves stdin dangling never reaches the stdin branch. Claude Code sets
  no `HOOK_PAYLOAD` and always writes real JSON to stdin, so it falls through correctly.
  The ordering is documented in the function as load-bearing.
- **Status**: `Resolved`

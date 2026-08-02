# Issues

<!-- Append-only, newest entry at the TOP, never rewrite old ones -- same discipline
as LOG.md. One entry per incident (the whole diagnose/fix sequence), written by the
systematic-debugging skill once its four-phase loop reaches a terminal state.
Format: ## YYYY-MM-DD HH:MM -- <short symptom title>, fields per the ISSUES.md section
of knowledge-manager's formats.md. Not preloaded at SessionStart -- consulted on demand. -->

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

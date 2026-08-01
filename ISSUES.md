# Issues

<!-- Append-only, newest entry at the TOP, never rewrite old ones -- same discipline
as LOG.md. One entry per incident (the whole diagnose/fix sequence), written by the
systematic-debugging skill once its four-phase loop reaches a terminal state.
Format: ## YYYY-MM-DD HH:MM -- <short symptom title>, fields per the ISSUES.md section
of knowledge-manager's formats.md. Not preloaded at SessionStart -- consulted on demand. -->

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

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

**Session's work reviewed and being committed.** `code-review` ran end to end for the
first time and caught a real defect pre-commit: `.claude/hooks/state/` was staged, which
would have churned every future commit and let `05-docs-gate.py` count its own
bookkeeping toward its work threshold. Now gitignored, files kept on disk. Signed off by
the user; receipt recorded on their authority.

**`.claude/README.md` and `.claude/PREREQUISITES.md` deleted, uncommitted.** Both
unreferenced; README duplicated `CLAUDE.md` and had already rotted (claimed two skills,
there are six). Two load-bearing facts salvaged into `CLAUDE.md` Gotchas. `KNOWN_FILES`
in `01-env-check.py` narrowed to the two settings files, verified by planting a stray.
`.claude/` now holds only `commands/`, `hooks/`, `routing/`, `skills/` and the two
settings files.

**`systematic-debugging` built, uncommitted.** Sixth skill, `6 entries routed`.
Workflow stage 4. Adopted from superpowers with three local adaptations: silence as
this repo's dominant symptom, "test the test before you trust it", and Phase 4 writing
`ISSUES.md`. That last one closes the gap that justified building it — `ISSUES.md` had
a format and no author since `error-recovery` was deleted. Header, `formats.md` and
`knowledge-manager`'s routing table all updated to name it.

Stage coverage now 1, 2, 4, 5, 6, 10, 11 owned. Still empty: **3 (research)**,
**7 (execution)**, 9 (optimization, arguably covered by `/simplify`), 12 (delivery,
mechanized by hooks). Next candidate is stage 7 `executing-plans` — `writing-plans`
currently hands off to a bare `general-purpose` agent.

**`knowledge-manager` rebuilt, uncommitted.** Fifth skill, `5 entries routed`.
Recovered `SKILL.md` + 204-line `formats.md` from `1443ba2^`, corrected two stale
facts in the spec, and added evidence-gathering (from `rjmurillo/ai-agents`
`session-end`) and write-for-an-outside-reader (from `christopherlouet/claude-base`
`session-handoff`). All four docs hooks now name the skill; two had dangling pronouns
left by the earlier de-naming sweep.

Immediately caught a real gap by using it: today's work had touched 3 of the 7
knowledge docs. Two incidents (the self-erasing review receipt, the YAML break that
deleted a description) and one decision (substring verb matching) had gone into
`LOG.md` prose instead of `ISSUES.md` and `decisions/`. Now filed properly.

**Review gate completed, uncommitted.** New skill `code-review` reviews a diff or
PR, reports findings, and requires sign-off before running
`03-review-gate.py --record`. The gate now also covers `gh pr create|merge|ready`,
fingerprinting the branch against its merge-base so a commit review cannot satisfy
a PR gate. Fourth skill, `4 entries routed`.

Fixed while doing it: **the gate had never been able to pass.**
`review-receipts.json` is tracked, so `--record` changed the fingerprint it had
just recorded under and every receipt self-invalidated. Receipts path now excluded
from all fingerprint inputs. Full cycle verified — ask → record → silent → edit →
ask → revert → silent.

Four suites pass, `compileall` 0, env-check `{"issues": []}`.

## Pending

- **Next skill to build: `systematic-debugging` (workflow stage 4).** `ISSUES.md` has
  a format and no author — its header still credits the deleted `error-recovery`
  skill. `knowledge-manager` shapes the entry; nothing produces the diagnosis. Adopt
  from `obra/superpowers` as `brainstormer` and `writing-plans` were. Runner-up:
  `executing-plans` (stage 7), ranked lower only because `writing-plans` has never
  run end to end. Stages 3 (research) and 9/12 are covered or lower value — see
  `docs/workflow.md`.

- **Nothing asserts that a name in a hook or skill resolves to something real.**
  22 dead references were cleared by hand at `1443ba2`; this is the repo's
  most-repeated failure and the only one with no automated guard. A check would
  grep `.claude/**` for backticked kebab-case tokens and `.claude/**` paths and
  assert each resolves. `tools/test_process_router.py` now does this for skill
  frontmatter only.
- **No skill has ever been run end to end.** Every gate, handoff and file path
  in the three SKILL.md files is asserted by its own text. The superpowers Iron
  Law — a baseline pressure run *without* the skill before writing it — is unmet
  on all three.
- **`04-delivery-guard.py` false-positives on Windows paths.**
  `find_ai_attribution` scans the whole command string and `_STANDALONE`
  excludes `/` but not `\`, so any path containing `\claude\` reads as AI
  attribution. Fix: add `\\` to both lookaround character classes.
- ~~`Stop` blocking is unproven in this build.~~ **Resolved 2026-08-01.** It blocked
  four times in one session. The Claude Code docs confirm `Stop` is blocking and
  `SessionEnd` is not, so `post-run/05-docs-gate.py` is on the correct event.
- **`changed_files()` is duplicated** across `pre-run/04-docs-staleness.py` and
  `post-run/05-docs-gate.py`, with a third near-copy in
  `pre-commit/05-docs-required.py`. `_hooklib.py` is where it belongs.
- **`docs/plans/` does not exist yet**; `writing-plans` writes there.
- **`docs/00-*.md … 17-*.md` describe the deleted layer.** Rebuild or delete;
  do not trust them.

## Next Steps

Nothing assigned. Pick from Pending.

## Open Questions

- Does the `agent:` frontmatter field actually dispatch a subagent? Supported
  and parses, but no skill uses it.
<!-- session-context:end -->

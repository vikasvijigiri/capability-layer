# Skill quality: no-slop vs affaan-m/ECC sweep skills

Comparables: `affaan-m/ECC` (public GitHub repo). Primary: `skills/config-gc/SKILL.md`
(closest match — a periodic sweep of accumulated dead weight across the config
tree, not a diff review, mirroring "reads standing artefacts including files
the change never touched"). Secondary: `skills/production-audit/SKILL.md` (a
standing-artefact readiness sweep with an explicit boundary against a
diff-level neighbour). Ruled out: `skills/plankton-code-quality/SKILL.md` is
write-time lint-on-edit, not a sweep; `skills/codehealth-mcp/SKILL.md` is a
per-file before/after gate, not a tree sweep; `skills/workspace-surface-audit/SKILL.md`
sweeps capability/config surface, not code slop. All five read in full via
`mcp__github__get_file_contents`.

## Gaps in ours (`.claude/skills/no-slop/SKILL.md`, 235 lines)

1. **Zero worked examples.** `production-audit` shows a full worked exchange
   (user question → response with score, `Blockers`, `High-value fixes`,
   `Evidence checked`, `Evidence missing`, `Next action`). `config-gc` shows
   five literal runnable scripts (orphan-hook detection, redundant-permission
   detection, soft-delete-with-undo, log-entry format). Ours never shows a
   filled finding row, a filled report table, or what a "clean" verdict line
   actually reads like — a new reader has to infer the shape from prescription
   alone (same gap the `writing-plans` pass found against ECC's `plan.md`).
   Fix: add one worked finding row (`file:line` · smell · break) and one
   worked "clean" verdict line.

2. **No persistent undo/log path for repairs.** `config-gc` is explicit:
   "Soft-delete first. Rename to `.disabled` > move to `_gc_trash/` > real
   deletion. Always keep an undo path," plus a permanent `gc_log.md` appended
   on every run ("timestamp, items actioned, undo instructions"). Ours (Phase
   2, lines 165–178) applies fixes and re-runs checks but states no undo
   mechanism beyond implicit git history, and no persistent log of what a
   given sweep repaired. Fix: state that Phase 2 repairs rely on git as the
   undo path explicitly (so it's asserted, not assumed) or add a log
   requirement for repeated sweeps.

3. **Approval is phase-grained, not item-grained.** Our gate (lines 63–77)
   is "Phase 1 REPORTS in full... Phase 2 repairs the local group only... after
   the user has seen every finding" — one approval covers the whole local
   batch. `config-gc` forces per-candidate confirmation ("Every candidate gets
   its own `[y/n/skip]` confirmation. No 'yes to all' shortcut") and names
   bulk approval as its #1 anti-pattern. Ours accepts this trade-off
   implicitly (the "local" group is scoped to mechanically-checkable,
   single-file changes, lower risk than config-gc's deletions) but never
   states *why* batch approval is safe here — a reader comparing the two
   would reasonably ask. Fix: one sentence justifying batch-vs-per-item by the
   local group's risk ceiling.

4. **Findings categories are prose, not a scannable table.** `production-audit`'s
   five risk lenses (Security And Auth, Data Integrity, Payments And Webhooks,
   Operations, User Experience) and `config-gc`'s eight-row channel table
   (channel → path → staleness signal) are both structured for skimming. Our
   six numbered categories (Overlapping responsibilities, Duplicate knowledge,
   God component, Orchestration leakage, Design-surface slop, Evidence slop —
   lines 102–126) are paragraph-form with no summary table, so a reader
   scanning for "which category applies to what I'm looking at" has to read
   all six paragraphs. Fix: prepend a two-column table (category → one-line
   signal) above the existing prose, which can stay as the detailed version.

## Where ours is stronger

1. **The sweep-vs-diff boundary is mechanically enforced, not just written.**
   Ours states the `code-review` boundary as a table (lines 18–25) *and*
   backs it with `tools/test_process_router.py`, which "fails if either
   neighbour stops naming the other" (line 33–34). `production-audit`'s
   equivalent boundary against `security-review` ("use security-review first")
   is prose only — nothing in the ECC repo checks that the two skills still
   cross-reference each other after an edit. `config-gc`'s boundary against
   `skill-stocktake` and `workspace-surface-audit` is likewise prose-only.

2. **Automated checks are wired into the sweep itself, not left to the
   reader's judgment.** Ours requires running `tools/run_checks.py --scoped`
   at the *start* of Phase 1 and *again* after Phase 2, and treats "no
   automated check for a category" as itself a finding (lines 81–90). None of
   the three ECC comparables tie their sweep to a repo-native check runner —
   `production-audit`'s "Evidence Checklist" is a fixed list of `git`
   commands to eyeball, not a pass/fail gate re-run after repairs.

3. **Structural vs local is a named, enforced split with routing, not just a
   caveat.** Ours requires every finding be filed as `local` (Phase-2-eligible)
   or `structural` (routed to planning, never applied here) with a table of
   examples (lines 153–163) and names the specific failure mode ("skipping to
   a task bakes in whichever came to mind first"). `config-gc` gets close with
   its soft-delete-first discipline but has no equivalent split between
   "safe to batch-fix now" and "needs its own planning pass" — every finding
   in `config-gc` is disposed of the same way (one-by-one confirm-or-skip).

## Verdict

`no-slop` out-engineers both ECC comparables on enforcement — a validator
pinning its neighbour boundary, a check-runner wired into both phases, and a
named local/structural split with routing — but ships zero worked examples
where both comparables show a filled report and runnable scripts, and states
no undo path where `config-gc` makes one explicit; the fix is to keep the
enforcement and borrow the worked example and the undo-path sentence.

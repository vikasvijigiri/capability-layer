---
name: debugging-memory-leak-detector
model: sonnet
description: Analyzes a memory profile/heap snapshot over time to find growing allocations and their retention paths. Use for "memory leak", "heap keeps growing", "OOM after running for a while", "find what's retaining memory", "it slows down over time", "crashes after running a while", "memory keeps climbing", "needs restarting every few days". Prefer this over raising the memory limit - that postpones the crash rather than finding what retains the memory. Do NOT use for a one-off high-memory spike with no growth trend. Scoped to a single diagnostic technique; for the overall bounded diagnose-fix-reverify loop on a repeatedly failing check, use `error-recovery`.
---

# Memory Leak Detector Skill

Diffs successive heap snapshots to find objects that grow without bound and traces their retention path.

## When to use
- "memory leak", "heap keeps growing", "OOM over time", "what's retaining memory"

## Steps
1. Diff `heap_snapshots` across time to find monotonically growing object types.
2. Trace the retention path (what's holding a reference) for top offenders.
3. Return `leak_report` with growth rate + retention chain per offender.

## Notes
A single snapshot cannot show a leak — always require at least two snapshots taken under comparable load.

## Routing

**Validator (required): `.claude/validators/debugging-hotfix.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/debugging-rca.md` - a matching blueprint takes precedence over a hand-built solution.

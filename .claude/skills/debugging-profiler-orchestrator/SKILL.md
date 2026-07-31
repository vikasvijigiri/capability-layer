---
name: debugging-profiler-orchestrator
model: sonnet
disallowed-tools: Edit, Write, NotebookEdit
description: Runs a CPU/memory profiler around a specified code region and summarizes hotspots. Use for "profile this", "why is this slow", "find the bottleneck", "CPU/memory hotspot", "performance regression", "it's slow", "takes forever", "what's eating all the time", "it used to be faster". Prefer this over guessing at the bottleneck - measured hotspots routinely contradict the obvious suspect. Do NOT use for a functional bug with no performance angle. Scoped to a single diagnostic technique; for the overall bounded diagnose-fix-reverify loop on a repeatedly failing check, use `error-recovery`.
effort: medium
---

# Profiler Orchestrator Skill

Wraps a target code region with a profiler run and summarizes hot functions/call trees.

## When to use
- "profile this", "why is this slow", "find the bottleneck", "CPU/memory hotspot"

## Steps
1. Select `profiler_type` (CPU/memory) based on the symptom.
2. Wrap `target_region` with profiling markers.
3. Run and collect the profile.
4. Summarize top hotspots + suggested next steps.

## Notes
Read-only measurement step — does not apply optimizations itself; hand results to implementation.

## Routing

**Validator (required): `.claude/validators/debugging-hotfix.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/debugging-rca.md` - a matching blueprint takes precedence over a hand-built solution.

---
name: work-decomposition
model: opus
description: Splits work into slices that can genuinely proceed independently, naming the contract each depends on and which can be delegated to a subagent. Use for "split this up", "can we parallelise this", "break this into pieces", "this is too big", "can two people work on this at once", "divide the work", "what can run in parallel", "can subagents do this". Prefer this over splitting by file or by person - work split without a frozen contract between the pieces produces merge conflicts and integration failure, not speed. Do NOT use for work that is genuinely sequential.
---

# Work Decomposition

## The one rule that matters

**Freeze the contract before splitting.** Two slices proceed independently only if neither
can change what the other depends on. Type definitions, API shapes, database columns, file
formats - written to disk first, then split. Work divided without that converges into a
merge conflict.

## Steps

1. **Identify the shared surface** - every type, route, table or file more than one slice
   touches.
2. **Freeze it.** Write the contract down as a real artefact before any slice starts. If it
   cannot be frozen yet, the work is not ready to split - say so.
3. **Cut along the frozen boundary**, not by domain fashion. A slice owns its files
   exclusively or it is not a slice.
4. **Classify each slice**: `delegable` (disjoint files, frozen contract, independently
   verifiable) or `main-context` (shared files, cross-cutting judgment, or integration).
5. **Keep integration in the main context, always.** Wiring slices together is exactly the
   work needing the whole picture, and the most common thing wrongly delegated.
6. **Name the verification per slice** - how it proves itself without the others.

## Output

A slice list with owner (`main` or a named agent), owned files, the contract it depends on,
and its independent verification. Feeds `execution-planner`'s parallel markings.

## Anti-patterns

- Splitting by layer (frontend/backend) when both sides of one feature move together.
- Delegating the slice you understand least. Delegation multiplies your clarity; it does
  not substitute for it.
- More than a handful of parallel slices - coordination cost overtakes the saving.

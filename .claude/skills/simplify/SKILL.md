---
name: simplify
model: sonnet
description: Reduces the complexity of working code - collapsing needless indirection, dead parameters, speculative abstraction and duplicated logic - without changing what it does. Use for "this is over-engineered", "why is this so complicated", "simplify this", "too many layers", "this could be much shorter", "do we need all this", "this is hard to follow", "reduce the complexity". Prefer this over leaving complexity that works - every unnecessary layer is paid for again by each person who reads it. Do NOT use for removing unused code, which is no-slop-check, or for restructuring without simplifying, which is safe-refactor.
effort: medium
---

# Simplify

Complexity in **live** code. `no-slop-check` finds code nobody calls; this finds code that
runs and does not need to be this shape.

## What to look for

- **Indirection with one implementation.** An interface, factory or strategy with exactly
  one concrete case is a layer charging rent for flexibility never used.
- **Parameters nobody varies.** A flag always passed `true` is not a parameter, it is two
  code paths, one of which is dead.
- **Speculative generality** - built for a case that has not arrived. YAGNI applies
  retroactively, not only at authoring time.
- **Duplicated logic that has drifted.** Two near-identical blocks are worse than either
  one copy or one abstraction, because the difference is invisible.
- **Nesting that a guard clause removes.** Depth is the most reliable readability signal.
- **Names requiring a comment to explain.** Rename rather than annotate.

## Rules

- **Behaviour must not change.** Establish a baseline first, exactly as `safe-refactor`
  does - the two skills share that requirement and are often used together.
- **Simpler is not shorter.** Clever one-liners that need decoding are complexity wearing a
  smaller footprint. Optimise for the reader, not the line count.
- **Do not simplify what you do not understand.** Code that looks redundant is sometimes
  load-bearing for a reason nobody documented; check `git log` and `decisions/` before
  removing it.
- Report what you chose *not* to simplify and why. A deliberate complexity that survives
  review is more valuable than one nobody examined.

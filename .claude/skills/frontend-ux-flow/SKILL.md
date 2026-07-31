---
name: frontend-ux-flow
model: opus
description: Designs what screens a feature needs, how a user moves between them, and where the flow can dead-end - before any component is built. Use for "what screens do we need", "design the user flow", "how does the user get from A to B", "map the journey", "where does this button go", "how should this be laid out across pages", "the navigation is confusing", "users get lost", "too many clicks to do anything". Prefer this over scaffolding components and discovering the flow afterwards - screens assembled bottom-up produce navigation nobody designed and dead-ends nobody noticed. Do NOT use for how a screen looks - that is `design-system` for tokens and `frontend-component-generator` for markup.
effort: high
---

# UX Flow Skill

Owns the layer above visual design - the set of screens, the paths between them, and
the states a user can get stuck in. `design-system` decides what a screen looks like;
this decides which screens exist at all.

## When to use
- "what screens do we need", "design the user flow", "map the journey", "users get lost"
- Before the first component of a new feature is scaffolded

## Steps
1. **Name the user's goal** as a task they complete, not a page they visit. "Publish a
   clip" is a goal; "the upload page" is not.
2. **List the screens/states the task passes through**, including the ones nobody
   designs - empty, loading, error, partial success, and the first-run case where the
   user has no data yet.
3. **Draw the transitions** between them, and mark every entry point (deep link,
   notification, back button, refresh mid-task).
4. **Find the dead-ends.** Every state needs a way forward and a way back. A state with
   neither is a bug, not a design choice.
5. **Count the steps to the primary goal** and cut any screen that exists only to
   confirm something reversible.
6. **Hand the screen list to `frontend-component-generator`** with each screen's states
   named, so the components get built for the real states rather than the happy path.

## Notes
The happy path is the easy part and the part that gets designed. Empty, error and
first-run states are where real UI quality is decided, so they are listed as first-class
screens here, not as afterthoughts on a component.

Refreshing mid-task and pressing back are the two transitions most often left undefined.
Check both explicitly.

## Routing

**Validator (required)** - `.claude/validators/frontend-visual-diff.md`. CLAUDE.md makes
this mandatory before any side effect is committed - it is not optional cleanup after the
fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a
matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to
end. It is a document to follow, not an executable - there is no workflow runtime in
Claude Code.

Requires a `DESIGN.md` downstream but not upstream - flows can be designed before tokens
exist. Run `design-system` before the first component is generated, not before this.

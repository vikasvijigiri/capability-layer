---
name: frontend-state-architecture
model: opus
description: Decides where client state lives, how data is fetched and cached, and how loading, empty and error states are represented - before components start holding state ad hoc. Use for "where should this state live", "do we need Redux/Zustand", "how should we fetch this", "server state vs client state", "prop drilling everywhere", "the data is out of sync", "two components disagree", "everything re-renders", "how do we handle loading". Prefer this over adding state to whichever component needed it first - state placed by convenience becomes the thing every later feature has to work around. Do NOT use to build one component's local state - that is `frontend-component-generator`.
---

# State Architecture Skill

Decides the client's data shape once, rather than letting it accumulate. Covers the
split between server state and client state, the fetching and caching policy, and how
non-happy states are represented.

## When to use
- "where should this state live", "do we need a state library", "the data is out of sync"
- "prop drilling everywhere", "everything re-renders", "two components disagree"
- Before the second component that needs the same data is written

## Steps
1. **Separate server state from client state.** Server state is a cache of something
   remote and needs staleness, refetch and invalidation rules. Client state is local
   (form drafts, open menus, selected tab) and needs none of that. Conflating them is
   the single most common cause of the mess this skill is invoked to fix.
2. **Place each piece of state at the lowest level that owns it.** Lift only when a
   second consumer genuinely appears - not in anticipation of one.
3. **Choose the fetching/caching layer** and state its policy explicitly - staleness
   window, refetch triggers, and what invalidates what after a mutation.
4. **Define the four states for every async read** - loading, empty, error, loaded.
   Name them as real UI states with real content, not as `isLoading` booleans.
5. **Decide the mutation story** - optimistic or pessimistic, and what the rollback is
   when the request fails. An optimistic update with no rollback is a data-loss bug.
6. **Name the re-render boundaries** so a change to one slice does not repaint the page.

## Notes
"Do we need a state library" is almost always the wrong first question. Answer step 1
first - most apps that reach for a global store actually needed a server-state cache,
and end up hand-rolling a worse one inside the store.

An error state that renders nothing is indistinguishable from a loading state that never
resolves. Every error state needs visible text and a retry path.

## Routing

**Validator (required)** - `.claude/validators/frontend-visual-diff.md`. CLAUDE.md makes
this mandatory before any side effect is committed - it is not optional cleanup after the
fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a
matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to
end. It is a document to follow, not an executable - there is no workflow runtime in
Claude Code.

Picking a state library or data-fetching framework for a new project is a stack decision -
use `stack-selector` and record the ADR. This skill decides the shape within a chosen
stack.

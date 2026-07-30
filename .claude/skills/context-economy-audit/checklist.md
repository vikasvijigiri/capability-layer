# The Context Economy Checklist

Each category names the real bug it was written from. Walk all of them; for each hit,
either fix it (as a separate, approved follow-up) or note in one line why it's a
deliberate exception.

## 1. Fixed per-turn cost
Any hook firing on every single turn (`UserPromptSubmit`) or every session
(`SessionStart`) is paid regardless of whether it's relevant that turn — this is the
highest-leverage category, fix here first.
- Measure its actual injected text length by running it, not reading the source and
  guessing.
- A `SessionStart` hook dumping a whole file's content when only a section/summary is
  needed (found: a hook re-injecting an entire `HANDOFF.md`, including its
  append-only `Completed` history, every single session).
- A hook re-injecting content Claude Code already loads by its own separate mechanism
  (found: a `SessionStart` hook re-printing the full project `CLAUDE.md`, which is
  already auto-loaded — pure duplication, paid twice for zero benefit).

## 2. Duplicated skills or hooks
Two skills/hooks doing overlapping work, or two files maintaining identical content
by hand.
- Compare each skill's stated `Capabilities`/responsibility against every other —
  genuine overlap is a finding; adjacent-but-distinct scope (e.g. a whole-repo sweep
  vs. a diff-scoped review) is not.
- A hand-maintained duplicate file (found: `AGENTS.md` kept as a byte-for-byte mirror
  of `CLAUDE.md` — same content, two things to keep in sync, one of them silently
  drifting).

## 3. Stale documentation
A companion `.md` doc, or a section of the global `CLAUDE.md`, describing behavior
the actual code no longer performs.
- Read the doc's claim, then read the implementation it describes, side by side —
  don't trust the doc's own confidence.
- Found twice already: a global `CLAUDE.md` "Loading strategy" section describing a
  `SessionStart` hook's old (already-fixed) behavior, and a hook's own companion
  `.md` making the same stale claim about itself.

## 4. Registry accuracy
The global `CLAUDE.md`'s Skill registry table vs. what's actually in
`.claude/skills/`; its Hook registry vs. `settings.json`'s actual `hooks` block.
- Every skill directory has exactly one row; every row has exactly one directory.
- Every registered hook (event + script) has exactly one line in the registry;
  nothing registered is undocumented, nothing documented is unregistered.

## 5. Pattern-matching correctness in hooks
Any hook using a regex/string match to gate or flag something.
- Don't just read the pattern — write a handful of realistic true-positive and
  true-negative test strings and actually run it.
- Found: a hook's AI-attribution regex (`\bclaude\b`) blocking any commit message
  that legitimately mentioned the filename `CLAUDE.md` — a real false positive that
  blocked a routine, legitimate commit, not a hypothetical edge case.

## 6. Judgment-reliability gaps
A skill the global `CLAUDE.md` calls a default, or says to use for "every X" /
"any non-trivial Y" — with no hook-level reminder backing it up.
- Skills are model-judgment-triggered; judgment silently not firing a relevant skill
  is a real, repeatable failure mode, not a hypothetical one (found twice in one
  session: a diff-review skill skipped before a commit, and a coordinating skill
  never invoked across an entire multi-step engineering task).
- Not automatically wrong to have no backstop — report it so it's a visible,
  deliberate choice instead of a silent gap.

## 7. Per-repo knowledge-doc bloat
`TASK.md`/`HANDOFF.md`/`LOG.md` growing well past what their own spec calls for.
- An "Active" task's `Done Checks`/`Status` field holding a full verification
  narrative that duplicates (at greater length) what `LOG.md` already records
  concisely.
- A `HANDOFF.md` section appearing outside where the format spec says it belongs,
  riding along with whatever "load this part" heuristic exists — the same failure
  class as Category 3, at the per-repo-doc layer instead of the global layer.

---

**The rule**: a byte count alone isn't a finding — explain why the size is a problem
(paid every turn/session, duplicates another source, no longer accurate) or it isn't
one yet.
